# Estrutura e implantação

## Experiment history

Start with the [visual chronological report](experiment_history_2026-10-13.html) to review interventions, results, parameter changes and missing historical records. Its current-run figures are a dated snapshot, not a live dashboard. Use the [benchmark guide](../benchmark/README.md) for the available interface and interrupted studies.

The [frozen Qwen3.6 generation base](qwen36_generation_base_2026-10-13.md) records the current parameters, input/output budgets and live transport/tokenization checks. Agent experiments will use a separate plan.

The [Qwen3.6 decision-contract round completed on 2026-10-14](../benchmark/results/rounds/decision_contract_qwen36_spark_2026-10-14/run_01/report.md) separates documentary completeness from operational success on the original 70 questions. It reused the approved generation base unchanged.

## Componentes

- `application/app.py`: entrada Streamlit.
- `application/presentation/`: UI, histórico local, fontes expansíveis e integrações.
- `application/service/rag/RagService.py`: fachada pública exclusiva V2.
- `application/service/rag/v2/`: engine, providers, agentes, fluxo, retrieval, evidências, coleções e planilhas.
- `application/service/LocalUploads.py`, `google_drive/`, `scraping/`: ingestão.
- `application/service/StructuredExtraction.py`: Markdown e sidecars de proveniência.
- `application/service/spreadsheet/`: conversão especializada de planilhas.
- `application/service/Bot.py`, `telegram/`: bot.
- `benchmark/`, `tests/`: avaliação e regressão.
- `config/`: configuração compartilhada e template de ambiente.
- `.streamlit/config.toml`: tema compartilhado da interface.

## Clone e ambiente Linux

```sh
git clone --depth 1 <URL_DO_REPOSITORIO> RAG_UFC
cd RAG_UFC
uv sync --frozen --no-dev
uv run --no-sync streamlit run application/app.py --server.address 127.0.0.1
```

Use Python 3.11. O lock mantém o índice PyTorch CUDA 12.8 já usado pelo projeto em Linux; isso não exige modificar drivers nesta tarefa. Embeddings e reranker executam na máquina da aplicação. A configuração atual usa CPU, inclusive quando o generator é remoto.

Na VM ATLab de 8 GB, vLLM já ocupa aproximadamente 7 GB de VRAM: preserve `rag_v2.device = "cpu"` para não competir pela GPU. Não há serviço distribuído ou container obrigatório.

A aplicação atual não oferece login. Ao disponibilizá-la externamente, configure o acesso pela rede/proxy da implantação.

## vLLM

Se aplicação e vLLM estiverem na mesma VM, `http://127.0.0.1:8000/v1` acessa o servidor diretamente.

Para aplicação local, mantenha VPN e túnel SSH ativos:

```sh
export VLLM_SSH_KEY=/caminho/local/da/chave
ssh -N -i "$VLLM_SSH_KEY" -L 8000:127.0.0.1:8000 root@10.101.53.209
```

A chave fica fora do repositório. O provider permite `VLLM_BASE_URL` e `VLLM_API_KEY` opcional.

Comando validado anteriormente para iniciar o modelo na RTX 2070 SUPER:

```sh
source /opt/vllm-env/bin/activate
vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ \
  --host 127.0.0.1 --port 8000 \
  --served-model-name Qwen/Qwen2.5-7B-Instruct-AWQ \
  --max-model-len 4096 --max-num-seqs 1 --enforce-eager
```

Não inicie outra instância se já houver um servidor. O smoke script faz um GET e uma geração; execute somente quando essa inferência for desejada:

```sh
uv run --no-sync python scripts/check_vllm.py
```

Esse smoke valida o transporte, não todas as perguntas/agentes. Os prompts completos, schemas e saída devem caber no contexto servido de 4096 tokens; o orçamento de contexto BGE não é uma contagem exata do tokenizer Qwen.

## Persistência

`data/collections/` contém Markdown, documentos originais e sidecars gerados por ingestão; `data/cache/` contém índices e estado OAuth. Histórico fica em `data/local_chat_sessions.json`. Credenciais locais ficam fora do Git.

Somente placeholders de `data/` são versionados. Transfira os documentos para a VM por upload ou Drive e preserve `data/` entre atualizações. Cache Hugging Face pode ocupar espaço adicional fora do projeto.

Telegram:

```sh
uv run --no-sync python -m application.service.Bot
```

## Limpeza

O V1 e seus runners foram removidos do código ativo. Helpers necessários foram migrados sem alterar o formato de chunks de planilhas ou o fingerprint documental V2. O histórico Git continua disponível; não foi reescrito.
