"""Exact FAISS scope search. No metadata post-filter or overfetch."""

from collections import OrderedDict
import time
import torch  # Load the shared OpenMP runtime before FAISS on macOS.
import faiss
import numpy as np


class ScopedDenseIndex:
    def __init__(self, vectors, chunks, fingerprint="", cache_bytes=128 * 1024**2):
        vectors = np.asarray(vectors, dtype="float32").copy()
        if (
            vectors.ndim != 2
            or len(vectors) != len(chunks)
            or not np.isfinite(vectors).all()
        ):
            raise ValueError("Invalid dense vectors")
        faiss.normalize_L2(vectors)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        self.chunks, self.fingerprint = chunks, fingerprint
        self.cache_bytes, self.used_bytes = cache_bytes, 0
        self.subsets = OrderedDict()
        self.last_search = {}

    def search(self, vector, scope, k):
        """None means whole collection; [] means explicitly empty scope."""
        started = time.perf_counter()
        query = np.asarray(vector, dtype="float32").reshape(1, -1).copy()
        if query.shape[1] != self.index.d or not np.isfinite(query).all():
            raise ValueError("Invalid query vector")
        faiss.normalize_L2(query)
        hit = False
        if scope is None:
            index, positions = self.index, list(range(len(self.chunks)))
        else:
            key = (self.fingerprint, tuple(sorted(set(scope))))
            if key in self.subsets:
                index, positions, size = self.subsets.pop(key)
                self.subsets[key] = (index, positions, size)
                hit = True
            else:
                allowed = set(scope)
                positions = [
                    i
                    for i, chunk in enumerate(self.chunks)
                    if chunk.document_id in allowed
                ]
                index = faiss.IndexFlatIP(self.index.d)
                if positions:
                    vectors = np.stack([self.index.reconstruct(i) for i in positions])
                    index.add(vectors)
                size = len(positions) * (self.index.d * 4 + 8)
                if size <= self.cache_bytes and size:
                    while self.subsets and self.used_bytes + size > self.cache_bytes:
                        _, (_, _, removed) = self.subsets.popitem(last=False)
                        self.used_bytes -= removed
                    self.subsets[key] = (index, positions, size)
                    self.used_bytes += size
        # Search the entire allowed subset to make score ties deterministic at K.
        # IndexFlatIP is exact; sorting stable IDs removes FAISS tie-order ambiguity.
        if not positions or k <= 0:
            results = []
        else:
            scores, local_ids = index.search(query, len(positions))
            results = [
                (positions[int(i)], float(score))
                for i, score in zip(local_ids[0], scores[0])
            ]
            results.sort(key=lambda item: (-item[1], self.chunks[item[0]].chunk_id))
            results = results[:k]
        self.last_search = {
            "strategy": "exact_scoped_subindex"
            if scope is not None
            else "exact_full_index",
            "allowed_count": len(positions),
            "subset_cache_hit": hit,
            "subset_cache_bytes": self.used_bytes,
            "latency_seconds": time.perf_counter() - started,
        }
        return results
