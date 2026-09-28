# Precisão e evidências

A implementação ativa é RAG V2. O documento anterior desta página descrevia melhorias do V1 e não correspondia ao pipeline atual.

Dense e sparse BGE-M3 são canais independentes, combinados por RRF e cross-encoder. Escopo documental é aplicado antes de top-K; parents são resolvidos por IDs persistidos. Planilhas preservam sua representação especializada.

A resposta factual usa claims vinculados a evidências e verificação. Fontes exibidas derivam dos claims aprovados. O foco visual é uma citação literal validada dentro do excerpt, sem alterar a evidência original.

Use [pipeline](pipeline.md) para arquitetura e [avaliação](benchmarking.md) para métricas e limitações. Remover o legado não constitui evidência de melhoria de acurácia; esta limpeza deve preservar o comportamento V2.
