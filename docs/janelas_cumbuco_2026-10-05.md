# Janelas operacionais observadas — Cumbuco, 05/10/2026

**Os 19 modelos foram tentados. Doze passaram na sondagem longa. Isso confirma entradas úteis observadas, não o contexto máximo nem qualidade de RAG.**

## Método

Uma chamada curta de calibração e, quando havia contagem de entrada válida, uma chamada longa por modelo. Temperatura zero, saída máxima 512, envelope `params`, leitura de códigos exclusivos no início/meio/fim. Os códigos não estavam na instrução da pergunta: tinham de ser recuperados do texto. Sucesso exige os três na resposta final, não só no campo de raciocínio.

Textos naturais do corpus existente. O controle curto contém 4.238 caracteres; o longo é dimensionado pela razão observada na calibração, mirando aproximadamente 80% do contexto. Essa razão **não é um tokenizer exato**. A tabela usa somente tokens reportados na resposta e recuperação literal, nunca caracteres convertidos em tokens.

Primeira condição: teto 32.768. Qwen 2.5 14B passou; Qwen Coder 32B atingiu timeout. Depois de uma pausa, retomada com teto 16.384 nos demais, respeitando os limites menores declarados. Portanto, não é comparação com prompts idênticos ou orçamento uniforme; é triagem operacional. Não houve alteração de provider, configuração do RAG, índice ou servidor.

## Resultados por modelo

Entrada validada significa maior entrada **reportada** em que os três códigos foram recuperados. Um número pequeno em controle curto não prova que essa seja a janela máxima.

| Modelo | Contexto solicitado no longo | Entrada longa reportada | Resultado |
| --- | ---: | ---: | --- |
| qwen2.5:14b | 32.768 | **31.205** | 3/3 códigos |
| qwen2.5-coder:32b | 32.768 | não reportada | Timeout; condição afetada pelo incidente descrito abaixo. Curto passou com 1.129 |
| phi4:latest | 16.384 | **15.019** | 3/3 códigos |
| phi3:latest | 16.384 | **14.147** | 3/3 códigos |
| llama4:latest | não executado | — | HTTP 200/JSON não objeto no controle curto |
| llama3.2:latest | 16.384 | **14.756** | 3/3 códigos |
| llama3.2-vision:latest | não executado | — | HTTP 200/JSON não objeto no controle curto |
| llama3.1:8b | 16.384 | **14.982** | 3/3 códigos |
| granite3-dense:8b | 4.096 | **3.771** | 3/3 códigos |
| granite3-dense:2b | 4.096 | 3.771 | 0/3 no longo; curto também falhou (2/3). Não atribuir isso apenas à janela |
| granite-code:8b | 16.384 | **15.594** | 3/3 códigos |
| gemma3:4b | 16.384 | **15.873** | 3/3 códigos |
| deepseek-r1:14b | 16.384 | **15.529** | 3/3 códigos |
| cow/gemma2_tools:2b | 8.192 | 0 | Longo sem resposta/uso útil; curto passou com 974 |
| glm-4.7-flash:latest | não executado | — | HTTP 200/JSON não objeto no controle curto |
| gpt-oss:20b | 16.384 | **14.760** | 3/3 códigos |
| qwen3.5:9b | 16.384 | 16.053 | Sem resposta final: atingiu 512 tokens de saída em raciocínio, tanto no curto quanto no longo |
| qwen3:14b | 16.384 | **15.215** | 3/3 códigos |
| qwen3:8b | 16.384 | **15.215** | 3/3 códigos |

Nenhum teste atestou as janelas nativas de 40 mil, 131 mil ou 262 mil. Essas capacidades continuam apenas declaradas nos metadados. Tampouco uma falha isolada fornece um limite superior: falhas de transporte, leitura/instrução, raciocínio e memória não são equivalentes.

## Incidente e limites de controle

Ao checar `--help`, o script inicial não possuía parser e iniciou uma segunda execução por engano. Esse processo local, criado pelo teste, foi encerrado; nenhum processo desconhecido foi finalizado. O CLI foi corrigido e `--help` foi conferido sem chamadas remotas. Pode ter ocorrido sobreposição na chamada longa do Qwen Coder 32B. **A condição afetada é inconclusiva e não fundamenta um limite do modelo.**

A chamada original do Coder registrou timeout de 180 s. Não se conhece a conclusão remota após fechamento da conexão; não houve acesso administrativo, cancelamento de modelos ou tentativa de contornar permissões. Após a pausa, as demais sondagens foram sequenciais do lado do cliente, com teto reduzido. Pelo incidente, possível carga residual e ausência de controle de outros usuários, **latências não são usadas para classificar velocidade ou hardware**.

Há 35 chamadas planejadas registradas (duas em 16 modelos e uma em três), mais a possível chamada duplicada do incidente, excluída da avaliação. Uma repetição por condição; sem estimativa estatística de estabilidade. Digest, prompts, hashes, parâmetros, uso, término, resposta e erros estão preservados, sem credenciais. O campo histórico `blocked_at=qwen2.5-coder:32b` pertence à primeira execução interrompida; `finished_at` registra a conclusão da retomada, que tentou os 19.

`finish_reason=stop` apareceu mesmo com teto de saída atingido ou resposta vazia. Isso não foi tratado como prova de completude. Os contadores são do servidor, não contagem independente do tokenizer. O contexto alocado/VRAM continuam não confirmados por falta de acesso à consulta de processos remotos.

## Aplicação prática

- Qwen 2.5 14B demonstrou uma faixa de entrada próxima de 32 mil neste teste.
- Phi-4, Qwen 3 8B/14B, GPT-OSS e outros passaram em entradas próximas de 14–16 mil. Há alternativas operacionais para controles RAG, sem afirmar superioridade semântica.
- Qwen 3 8B/14B e GPT-OSS completaram com saída 512, ao contrário da sondagem anterior com 128. Orçamento de saída/raciocínio é uma variável separada da janela de entrada.
- Qwen 3.5 precisa de uma investigação específica de raciocínio/saída antes de concluir que sua grande janela declarada é útil para os agentes atuais.
- Modelos que retornaram JSON inválido ou uso zero não receberam uma janela validada por inferência.

Próximo experimento: controles negativos e cobertura por requisitos, com configuração congelada e orçamento comparável. Leitura de três códigos não valida planejamento, multi-hop ou suporte de claims. A configuração atual do RAG permaneceu inalterada e o benchmark de 80 casos não foi executado.

## Reprodução

Script: `scripts/measure_cumbuco_windows.py`. Resultados operacionais ignorados pelo Git: `benchmark/results/runs/cumbuco_windows_all_2026-10-05/results.json`.

```sh
uv run --no-sync python scripts/measure_cumbuco_windows.py --help
```

O script retoma checkpoints existentes; um timeout interrompe a execução e impede seguir automaticamente. `--skip-model` e `--max-context` foram usados na retomada documentada. Para uma nova condição independente, passar `--output` apontando para um arquivo em novo diretório; não apagar evidências de falhas anteriores. Compilação, formatação e checagem do diff passaram. Dois testes locais verificam marcadores e que `--help` nunca cria uma sessão HTTP.
