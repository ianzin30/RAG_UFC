# Avaliação V2

Testes unitários usam fakes e fixtures controladas:

```sh
uv sync --frozen
uv run python -m pytest -q
```

Runners abaixo são ferramentas explícitas de avaliação: alguns carregam modelos BGE e os modos de geração consomem inferência. A limpeza do repositório não os executa.

## Runners mantidos

```sh
# Retrieval sintético com queries fixas, sem generator
uv run python -m benchmark.v2 --output benchmark/results/v2_retrieval.json

# Geração sintética: provider/modelo da configuração por default
uv run python -m benchmark.v2 --generate

# Override explícito de desenvolvimento
uv run python -m benchmark.v2 --generate --provider ollama --model phi4:latest

# Corpus real previamente carregado
uv run python -m benchmark.real_corpus --collection uploaded_files
uv run python -m benchmark.real_generation --collection uploaded_files

# Estudo de perguntas anotadas e relatório
uv run python -m benchmark.run --questions benchmark/questions.json
```

As perguntas do estudo ficam em JSON; veja `benchmark/questions.json` para o contrato. Anotações de corpus real são puladas quando os documentos exigidos estão ausentes. Documentos operacionais não são publicados junto do repositório.

## Métricas e diagnostics

O runner sintético separa retrieval fixo de geração/agentes e calcula Recall@K, MRR, nDCG, Evidence Recall e Complete Evidence Recall. O corpus real usa anotações documentais: seu Complete Evidence Recall mede documentos necessários, não prova todas as relações internas.

Geração registra acerto determinístico por termos/abstenção, claims, citações e chamadas de providers. Os julgamentos semânticos suplementares nunca sobrescrevem métricas determinísticas. Presença de IDs de citação não equivale, sozinha, a prova de suporte semântico.

Relatórios incluem configuração e diagnostics disponíveis. Resultados de Phi-4, Qwen local e vLLM são específicos de seus modelos. Fixtures sintéticas não demonstram qualidade em produção.

Resultados ficam em `benchmark/results/`, ignorado por Git. Não publique traces ou documentos privados inadvertidamente.

## Histórico

Runners V1 e grid baseado no splitter antigo foram aposentados. Resultados históricos locais foram preservados; para consultar a implementação antiga, use o histórico Git anterior à limpeza. A árvore V2 anterior à limpeza ainda não tinha sido commitada, portanto não se deve atribuir todos os seus resultados a um commit existente.

Não há promessa de reproduzir o baseline V1 a partir da instalação V2 atual. Os testes e runners preservados avaliam a implementação ativa.
