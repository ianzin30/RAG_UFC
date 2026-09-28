# Limpeza para implantação V2

## Inventário

- Retirados do índice Git: `.claude`, `.claire`, seus gitlinks, `.DS_Store` e `null`. Cópias locais permanecem no disco.
- Removidos do código: 37 arquivos RAG legados (6.937 linhas no último commit, antes da migração), runners exclusivos de baseline V1, grid V1 e seis arquivos de testes desse pipeline.
- Migrados: coleção/hash/carga para `v2/Collections.py`, chunks especializados para `v2/Spreadsheet.py`, normalização para `v2/Support.py` e callbacks para a fachada.
- Configuração ativa: `[llm]`, providers/roles, `[rag_v2]` e opções de modelos. O alias `ufc_model_name` continua somente para compatibilidade de leitura.
- Removidas dependências diretas inativas e 35 pacotes do lock. As versões restantes foram preservadas. O lock atual conserva CrewAI 1.14.0, que o resolvedor sinaliza como yanked; não foi feita atualização de framework nesta limpeza.

## Conjunto destinado ao commit

Manter `.gitignore`, `.python-version`, `.streamlit/config.toml`, READMEs, `application/`, `benchmark/`, `tests/`, `scripts/check_vllm.py`, `config/config.toml`, `config/.env.example`, placeholders de `data/`, `pyproject.toml` e `uv.lock`.

As adições V2, `StructuredExtraction.py`, runners V2, testes e script de smoke estavam sem rastreamento antes desta limpeza. A sequência de commits inclui esses componentes junto da migração da fachada e das integrações; não apenas a retirada do legado.

O conjunto revisado foi organizado em commits temáticos para publicação por solicitação do mantenedor. O histórico Git foi preservado; clone raso limita seu download.

## Validação

Baseline: 161 testes. Os testes exclusivos V1 foram aposentados; sua redução não representa perda ou ganho de acurácia V2. Foram acrescentadas verificações de coleções, configuração, planilhas, fachada/callbacks e rotas casual/follow-up atuais.

Um snapshot temporário inclui somente os arquivos destinados ao repositório, sem `.env`, corpus, caches, worktrees ou ambientes locais. Testes, imports, CLI help e inicialização Streamlit são verificados nesse snapshot usando o ambiente Python já instalado; não é uma instalação Linux independente.

Nenhum benchmark, download de modelo, inferência real ou mudança na VM faz parte desta validação. Documentos e caches locais foram preservados. Veja `docs/README.md` para instalação e limitações de memória/contexto do vLLM.
