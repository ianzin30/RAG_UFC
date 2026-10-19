import numpy as np
import pytest
from application.service.rag.v2.Dense import ScopedDenseIndex
from application.service.rag.v2.Models import Chunk
from application.service.rag.v2.Retrieval import SparseIndex, reciprocal_rank_fusion


def chunks(n):
    return [
        Chunk(
            chunk_id=str(i),
            document_id="allowed" if i < 2 else "outside",
            document_name=str(i),
            parent_id=str(i),
            text="test",
        )
        for i in range(n)
    ]


def test_dense_prefilter_matches_exact_subset_despite_outside_distractors():
    vectors = np.array([[0.1, 0.9], [0.2, 0.8]] + [[1, 0]] * 100, dtype="float32")
    docs = chunks(len(vectors))
    index = ScopedDenseIndex(vectors, docs)
    result = index.search([1, 0], ["allowed"], 30)
    normalized = vectors[:2] / np.linalg.norm(vectors[:2], axis=1, keepdims=True)
    assert [i for i, _ in result] == [1, 0]
    assert [s for _, s in result] == pytest.approx(normalized[[1, 0], 0])
    assert index.search([1, 0], [], 3) == []
    assert index.search([1, 0], ["missing"], 3) == []
    index.search([1, 0], ["allowed"], 3)
    assert index.last_search["subset_cache_hit"]


def test_dense_ties_scope_union_and_cache_budget():
    index = ScopedDenseIndex([[1, 0]] * 4, chunks(4), cache_bytes=24)
    assert [i for i, _ in index.search([1, 0], ["outside", "allowed"], 2)] == [0, 1]
    assert index.used_bytes <= 24


def test_sparse_matches_official_installed_score():
    from FlagEmbedding import BGEM3FlagModel

    query, document = {"42": 0.3, "7": 2.0}, {"42": 0.4, "7": 0.5, "99": 4.0}
    official = BGEM3FlagModel.compute_lexical_matching_score(None, query, document)
    index = SparseIndex([document, {"999": 1}, document], chunks(3))
    assert index.search(query, ["allowed"], 10) == [(0, pytest.approx(official))]
    assert index.search({}, None, 10) == []
    assert index.search(query, [], 10) == []


def test_rrf_deduplicates_and_keeps_both_ranks():
    result = reciprocal_rank_fusion(
        [(0, 100), (1, 90)], [(1, 0.2), (0, 0.1)], chunks(2)
    )
    assert len(result) == 2
    assert result[0]["chunk_id"] == "0"
    assert result[0]["rrf_score"] == pytest.approx(1 / 61 + 1 / 62)
    assert (result[0]["dense_rank"], result[0]["sparse_rank"]) == (1, 2)


def test_reranker_order_is_preserved_in_diagnostics():
    from application.service.rag.v2.Retrieval import HybridRetriever
    from application.service.rag.v2.Config import V2Config

    class Encoder:
        def encode(self, texts):
            return [[1, 0]], [{"x": 1}]

    class Reranker:
        def score(self, query, texts):
            return [0, 10]

    engine = HybridRetriever(
        chunks(2),
        [[1, 0], [0.5, 0.5]],
        [{"x": 1}, {"x": 0.5}],
        Encoder(),
        Reranker(),
        V2Config(),
    )
    ranked, trace = engine.search("question", None, 1)
    assert [item["position"] for item in ranked] == [1, 0]
    assert [item["reranker_score"] for item in trace["stages"]["reranker"]] == [10, 0]
    assert trace["stages"]["rrf"][0]["position"] == 0


@pytest.mark.parametrize("overlap", [0, 10])
@pytest.mark.parametrize("rerank_k", [30, 60])
def test_full_union_allows_evidence_beyond_initial_cutoff(monkeypatch, overlap, rerank_k):
    from application.service.rag.v2.Config import V2Config
    from application.service.rag.v2.Retrieval import HybridRetriever

    docs = chunks(60)
    for chunk in docs:
        chunk.text = "evidence " + chunk.chunk_id
    dense = [(i, 1.0) for i in range(30)]
    sparse = [(i, 1.0) for i in range(30 - overlap, 60 - overlap)]
    fused = reciprocal_rank_fusion(dense, sparse, docs)
    target = docs[fused[-1]["position"]].text

    class Encoder:
        def encode(self, texts):
            return [[1, 0]], [{"x": 1}]

    class Reranker:
        received = None

        def score(self, query, texts):
            self.received = texts
            return [10 if text == target else 0 for text in texts]

    reranker = Reranker()
    engine = HybridRetriever(
        docs, [[1, 0]] * 60, [{}] * 60, Encoder(), reranker,
        V2Config(embedding_provider="ollama", search_k=30, rerank_k=rerank_k),
    )
    search_calls = []

    def ranking(channel, result):
        def search(query, scope, k):
            search_calls.append((channel, scope, k))
            return result
        return search

    monkeypatch.setattr(engine.dense, "search", ranking("dense", dense))
    monkeypatch.setattr(engine.sparse, "search", ranking("sparse", sparse))
    ranked, trace = engine.search("question", ["allowed"], 1)

    assert search_calls == [("dense", ["allowed"], 30), ("sparse", ["allowed"], 30)]
    assert reranker.received == [docs[item["position"]].text for item in fused[:rerank_k]]
    assert len(set(reranker.received)) == len(reranker.received)
    assert trace["candidate_counts"] == {
        "dense": 30, "sparse": 30, "union": 60 - overlap,
        "reranked": min(rerank_k, 60 - overlap),
    }
    if rerank_k == 60:
        assert docs[ranked[0]["position"]].text == target
    else:
        assert target not in reranker.received
