"""Deterministic stand-ins: no model, tokenizer download or network in package tests."""
import re

import numpy as np
import pytest

from rag_ufc_core import EngineSettings


class WordTokenizer:
    name_or_path = "test/word-tokenizer"

    def __call__(self, text, **kwargs):
        return {"offset_mapping": [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]}


class HashEncoder:
    """Fixed-size bag-of-words vectors and sparse weights."""

    identity = {"provider": "test", "model": "hash-encoder", "dimensions": 16}
    tokenizer = WordTokenizer()

    def encode(self, texts):
        vectors, sparse = [], []
        for text in texts:
            words = re.findall(r"\w+", text.lower())
            vector = np.zeros(16, dtype="float32")
            for word in words:
                vector[sum(map(ord, word)) % 16] += 1.0
            vectors.append(vector + 1e-3)
            sparse.append({word: 1.0 for word in words})
        return np.asarray(vectors), sparse


@pytest.fixture
def settings():
    return EngineSettings.from_release({"llm": {"providers": {"spark": {"base_url": "https://llm.invalid/api"}}}})


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "data" / "collections" / "uploaded_files"
    root.mkdir(parents=True)
    (root / "01_regimento.md").write_text(
        "# regimento.pdf\n\nO colegiado do curso se reúne mensalmente.\n\n"
        "## Coordenação\n\nA coordenação do AFO cabe ao professor responsável.\n",
        encoding="utf-8",
    )
    (root / "02_calendario.md").write_text(
        "# calendario.pdf\n\nO semestre começa em março e termina em julho.\n", encoding="utf-8"
    )
    return tmp_path / "data"
