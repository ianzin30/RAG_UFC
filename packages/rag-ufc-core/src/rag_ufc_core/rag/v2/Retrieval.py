"""BGE adapters and deterministic sparse/RRF/reranking pipeline."""

from collections import defaultdict
import importlib.metadata
import time
import numpy as np
from .Dense import ScopedDenseIndex


class BGEEncoder:
    def __init__(self, config):
        from FlagEmbedding import BGEM3FlagModel

        self.config = config
        self.model = BGEM3FlagModel(
            config.embedding_model,
            devices=config.device,
            use_fp16=config.device != "cpu",
        )
        self.tokenizer = self.model.tokenizer
        self.identity = {
            "model": config.embedding_model,
            "library": "FlagEmbedding",
            "version": importlib.metadata.version("FlagEmbedding"),
            "revision": getattr(self.model.model.config, "_commit_hash", None),
        }

    def encode(self, texts):
        output = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            max_length=self.config.child_tokens + 128,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        return output["dense_vecs"], [
            {str(token): float(weight) for token, weight in weights.items()}
            for weights in output["lexical_weights"]
        ]


class SparseIndex:
    """Sum of shared-token weight products, identical to FlagEmbedding 1.3.5."""

    def __init__(self, weights, chunks):
        self.chunks = chunks
        self.postings = defaultdict(list)
        for i, document in enumerate(weights):
            for token, weight in document.items():
                if weight > 0:
                    self.postings[str(token)].append((i, float(weight)))

    def search(self, query, scope, k):
        allowed = None if scope is None else set(scope)
        scores = defaultdict(float)
        for token, query_weight in query.items():
            for i, document_weight in self.postings.get(str(token), ()):
                if allowed is None or self.chunks[i].document_id in allowed:
                    scores[i] += float(query_weight) * document_weight
        return sorted(
            ((i, score) for i, score in scores.items() if score > 0),
            key=lambda item: (-item[1], self.chunks[item[0]].chunk_id),
        )[:k]


def create_encoder(config):
    bge = BGEEncoder(config)
    if config.embedding_provider == "ollama":
        from .OllamaEmbeddings import OllamaHybridEncoder

        return OllamaHybridEncoder(config, bge)
    return bge


def reciprocal_rank_fusion(dense, sparse, chunks, k=60):
    results = {}
    for channel, ranking in (("dense_rank", dense), ("sparse_rank", sparse)):
        seen = set()
        for rank, (position, _) in enumerate(ranking, 1):
            chunk_id = chunks[position].chunk_id
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            item = results.setdefault(
                chunk_id,
                {
                    "position": position,
                    "chunk_id": chunk_id,
                    "rrf_score": 0.0,
                    "dense_rank": None,
                    "sparse_rank": None,
                },
            )
            item[channel] = rank
            item["rrf_score"] += 1 / (k + rank)
    return sorted(
        results.values(), key=lambda item: (-item["rrf_score"], item["chunk_id"])
    )


class BGEReranker:
    def __init__(self, config):
        self.config = config
        self.model = None

    def score(self, query, texts):
        from sentence_transformers import CrossEncoder

        if self.model is None:
            self.model = CrossEncoder(
                self.config.reranker_model,
                device=self.config.device,
                max_length=self.config.child_tokens + 128,
            )
        if not texts:
            return []
        import torch

        return (
            np.asarray(
                self.model.predict(
                    [(query, text) for text in texts],
                    batch_size=self.config.batch_size,
                    activation_fn=torch.nn.Identity(),
                    show_progress_bar=False,
                )
            )
            .reshape(-1)
            .tolist()
        )


class HybridRetriever:
    def __init__(
        self, chunks, vectors, weights, encoder, reranker, config, fingerprint=""
    ):
        self.chunks, self.encoder, self.reranker, self.config = (
            chunks,
            encoder,
            reranker,
            config,
        )
        self.dense = ScopedDenseIndex(
            vectors, chunks, fingerprint, config.subset_cache_mb * 1024**2
        )
        self.sparse = SparseIndex(weights, chunks)

    def search(self, query, scope, hop):
        stages, latencies = {}, {}
        started = time.perf_counter()
        encode_query = getattr(self.encoder, "encode_query", self.encoder.encode)
        vectors, weights = encode_query([query])
        latencies["query_encoding"] = time.perf_counter() - started
        started = time.perf_counter()
        dense = self.dense.search(vectors[0], scope, self.config.search_k)
        latencies["dense"] = time.perf_counter() - started
        started = time.perf_counter()
        sparse = self.sparse.search(weights[0], scope, self.config.search_k)
        latencies["sparse"] = time.perf_counter() - started
        for name, ranking in (("dense", dense), ("sparse", sparse)):
            stages[name] = [
                {"chunk_id": self.chunks[i].chunk_id, "score": score}
                for i, score in ranking
            ]
        started = time.perf_counter()
        fused = reciprocal_rank_fusion(dense, sparse, self.chunks, self.config.rrf_k)
        stages["rrf"] = [dict(item) for item in fused]
        latencies["rrf"] = time.perf_counter() - started
        candidates = [dict(item) for item in fused[: self.config.rerank_k]]
        started = time.perf_counter()
        scores = self.reranker.score(
            query, [self.chunks[item["position"]].text for item in candidates]
        )
        if len(scores) != len(candidates) or not np.isfinite(scores).all():
            raise ValueError("Invalid reranker output; no silent ranking fallback")
        for item, score in zip(candidates, scores):
            item["reranker_score"] = float(score)
        candidates.sort(key=lambda item: (-item["reranker_score"], item["chunk_id"]))
        stages["reranker"] = candidates
        latencies["reranker"] = time.perf_counter() - started
        return candidates, {
            "hop_id": hop,
            "query": query,
            "scope": scope,
            "stages": stages,
            "latencies": latencies,
            "dense_filter": self.dense.last_search,
            "candidate_counts": {
                "dense": len(dense), "sparse": len(sparse),
                "union": len(fused), "reranked": len(candidates),
            },
        }
