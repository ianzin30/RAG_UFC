# RAG UFC

Aplicação Streamlit com RAG V2, ingestão local/Google Drive, scraping e Telegram.

## Executar

Python 3.11 e [uv](https://docs.astral.sh/uv/) são necessários.

```sh
uv sync --frozen --no-dev
uv run --no-sync streamlit run application/app.py
```

A configuração sem segredos está em `config/config.toml`. Para credenciais de integrações, copie `config/.env.example` para `.env` e preencha somente o necessário. vLLM sem autenticação não exige API key.

O primeiro carregamento de uma coleção baixa os modelos BGE de embedding/reranking, se ainda não estiverem no cache externo do Hugging Face. Documentos e índices são criados em `data/` e não acompanham o clone.

## Arquitetura e instalação na VM

- [Estrutura e implantação](docs/README.md)
- [Pipeline V2](docs/pipeline.md)
- [Configuração](config/README.md)
- [Avaliação](docs/benchmarking.md)
- [Precisão e evidências](docs/document_retrieval_precision.md)

## Desenvolvimento

```sh
uv sync --frozen
uv run python -m pytest -q
```

O repositório mantém testes, fixtures e ferramentas V2. O pipeline V1 foi aposentado; resultados históricos locais não são apagados.
