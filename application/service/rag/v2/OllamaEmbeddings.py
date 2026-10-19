"""EmbeddingGemma dense vectors with BGE lexical weights and chunk tokenizer.

Only the dense channel changes. Keeping the BGE tokenizer and sparse encoder
allows controlled comparison without rechunking or changing lexical retrieval.
"""

import numpy as np
import requests


class OllamaHybridEncoder:
    QUERY_PREFIX = "task: search result | query: "
    DOCUMENT_PREFIX = "title: none | text: "

    def __init__(self, config, sparse_encoder, session=None):
        if config.embedding_ollama_model.split(":", 1)[0] != "embeddinggemma":
            raise ValueError("This adapter supports EmbeddingGemma prompt formatting only")
        self.config = config
        self.sparse_encoder = sparse_encoder
        self.tokenizer = sparse_encoder.tokenizer
        self.session = session or requests.Session()
        self.base_url = config.embedding_ollama_base_url.rstrip("/")
        self.model = config.embedding_ollama_model
        info = self._model_info()
        version = self._get("version")["version"]
        self.identity = {
            "provider": "ollama_dense_bge_sparse",
            "model": self.model, "digest": info["digest"],
            "quantization": info["details"]["quantization_level"],
            "dimensions": 768, "ollama_version": version,
            "base_url": self.base_url,
            "query_prefix": self.QUERY_PREFIX,
            "document_prefix": self.DOCUMENT_PREFIX,
            "truncate": False, "sparse_encoder": sparse_encoder.identity,
        }

    def _get(self, route):
        response = self.session.get(
            f"{self.base_url}/api/{route}", timeout=self.config.embedding_timeout_seconds)
        response.raise_for_status()
        return response.json()

    def _model_info(self):
        tag = self.model if ":" in self.model else self.model + ":latest"
        for model in self._get("tags")["models"]:
            if model["name"] == tag:
                if "embedding" not in model.get("capabilities", ["embedding"]):
                    raise ValueError("Selected Ollama model does not support embeddings")
                return model
        raise ValueError(f"Ollama embedding model is not installed: {tag}")

    def verify_model_unchanged(self):
        if self._model_info()["digest"] != self.identity["digest"]:
            raise RuntimeError("Ollama embedding model changed during this experiment")

    def encode_dense(self, texts, *, query=False):
        prefix = self.QUERY_PREFIX if query else self.DOCUMENT_PREFIX
        vectors = []
        for start in range(0, len(texts), self.config.batch_size):
            batch = texts[start:start + self.config.batch_size]
            response = self.session.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": [prefix + text for text in batch],
                      "truncate": False, "keep_alive": "30m"},
                timeout=self.config.embedding_timeout_seconds,
            )
            response.raise_for_status()
            values = np.asarray(response.json()["embeddings"], dtype="float32")
            if (values.shape != (len(batch), 768) or not np.isfinite(values).all()
                    or np.any(np.linalg.norm(values, axis=1) == 0)):
                raise ValueError("Invalid Ollama embeddings; no silent fallback")
            vectors.append(values)
        return np.concatenate(vectors) if vectors else np.empty((0, 768), dtype="float32")

    def encode(self, texts):
        vectors = self.encode_dense(texts)
        _, sparse = self.sparse_encoder.encode(texts)
        return vectors, sparse

    def encode_query(self, texts):
        vectors = self.encode_dense(texts, query=True)
        _, sparse = self.sparse_encoder.encode(texts)
        return vectors, sparse
