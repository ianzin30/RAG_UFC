import numpy as np
import pytest

from application.service.rag.v2.Config import V2Config
from application.service.rag.v2.OllamaEmbeddings import OllamaHybridEncoder


class SparseEncoder:
    tokenizer = object()
    identity = {'model': 'BAAI/bge-m3'}

    def encode(self, texts):
        return np.zeros((len(texts), 1024)), [{'42': 0.5} for _ in texts]


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class Session:
    def __init__(self):
        self.posts = []
        self.digest = 'fixed-model-digest'
        self.dimensions = 768
        self.value = 1

    def get(self, url, **kwargs):
        if url.endswith('/tags'):
            return Response({'models': [{'name': 'embeddinggemma:latest',
                                         'digest': self.digest, 'capabilities': ['embedding'],
                                         'details': {'quantization_level': 'BF16'}}]})
        return Response({'version': '0.34.3'})

    def post(self, url, json, **kwargs):
        self.posts.append(json)
        return Response({'embeddings': [[self.value] * self.dimensions for _ in json['input']]})


def test_ollama_uses_query_and_document_prompts_and_preserves_sparse_encoder():
    session, sparse = Session(), SparseEncoder()
    encoder = OllamaHybridEncoder(V2Config(batch_size=2), sparse, session)
    documents, weights = encoder.encode(['um', 'dois', 'três'])
    query, query_weights = encoder.encode_query(['pergunta'])
    assert documents.shape == (3, 768) and query.shape == (1, 768)
    assert session.posts[0]['input'] == ['title: none | text: um', 'title: none | text: dois']
    assert session.posts[-1]['input'] == ['task: search result | query: pergunta']
    assert all(p['truncate'] is False for p in session.posts)
    assert encoder.tokenizer is sparse.tokenizer
    assert weights == [{'42': 0.5}] * 3 and query_weights == [{'42': 0.5}]


@pytest.mark.parametrize('dimensions,value', [(1024, 1), (768, float('nan')), (768, 0)])
def test_ollama_rejects_invalid_vectors_without_fallback(dimensions, value):
    session = Session()
    session.dimensions, session.value = dimensions, value
    encoder = OllamaHybridEncoder(V2Config(), SparseEncoder(), session)
    with pytest.raises(ValueError, match='Invalid Ollama embeddings'):
        encoder.encode_dense(['pergunta'], query=True)


def test_ollama_rejects_model_change_during_run():
    session = Session()
    encoder = OllamaHybridEncoder(V2Config(), SparseEncoder(), session)
    session.digest = 'changed'
    with pytest.raises(RuntimeError, match='changed during'):
        encoder.verify_model_unchanged()
