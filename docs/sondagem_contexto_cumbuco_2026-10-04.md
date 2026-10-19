# Contexto dos modelos Cumbuco — 04/10/2026

## Método e limites

Consulta autenticada de `/api/models` e `/ollama/api/show` para os 19 modelos expostos. Somente campos técnicos foram preservados; nenhuma credencial ou ACL de usuários foi gravada no resultado. O contexto de `model_info` é capacidade declarada do artefato, não confirmação de memória disponível ou janela operacional no servidor.

Depois: cinco modelos, duas condições por modelo, **uma repetição por condição**, chamadas sequenciais. Mesmo texto português (36.869 caracteres), três marcadores literais distribuídos no início/meio/fim, temperatura zero, envelope `params`, limite de saída 128, contextos solicitados 8.192 e 16.384. Texto/proveniência/identidades e respostas estão em `benchmark/results/runs/cumbuco_context_models_2026-10-04/probe.json` (arquivo operacional ignorado).

O texto vem de `natural_prompt(200)` do harness existente, mas nenhuma pergunta do benchmark, planner, retrieval ou verificador foi executada. Caracteres não foram tratados como tokens. Cada tokenizer produz uma contagem diferente para o mesmo texto. Não houve mudança na configuração do RAG, modelo ativo configurado, servidor ou índice. Chamadas de geração podem carregar modelos no servidor; não houve unload, reinicialização ou ajuste administrativo.

O endpoint `/ollama/api/ps` respondeu **401**: não foi possível confirmar contexto alocado ou VRAM em execução. Não houve tentativa de contornar essa permissão.

## Capacidades declaradas pelos artefatos instalados

| Modelo | Contexto declarado (tokens) |
| --- | ---: |
| phi4:latest | 16.384 |
| qwen2.5:14b | 32.768 |
| qwen2.5-coder:32b | 32.768 |
| qwen3:8b | 40.960 |
| qwen3:14b | 40.960 |
| qwen3.5:9b | 262.144 |
| gpt-oss:20b | 131.072 |
| deepseek-r1:14b | 131.072 |
| glm-4.7-flash:latest | 202.752 |
| gemma3:4b | 131.072 |
| llama3.1:8b | 131.072 |
| llama3.2:latest | 131.072 |
| llama3.2-vision:latest | 131.072 |
| llama4:latest | 10.485.760 |
| phi3:latest | 131.072 |
| granite3-dense:8b | 4.096 |
| granite3-dense:2b | 4.096 |
| granite-code:8b | 128.000 |
| cow/gemma2_tools:2b | 8.192 |

Phi-3 e GPT-OSS também reportam `rope.scaling.original_context_length=4096`; a tabela usa o campo principal, não presume qualidade uniforme em toda a extensão. Não foi tentado carregar os maiores modelos nem validar janelas de centenas de milhares/milhões de tokens.

## Geração real: mesmas condições de transporte

Todos os dez pedidos com saída 128 responderam HTTP 200.

| Modelo | Entrada reportada com pedido 8.192 | Marcadores recuperados | Entrada reportada com pedido 16.384 | Marcadores recuperados |
| --- | ---: | ---: | ---: | ---: |
| phi4:latest | 8.192 | 1/3 (fim) | 9.980 | 3/3 |
| qwen2.5:14b | 8.192 | 1/3 (fim) | 10.133 | 3/3 |
| qwen3.5:9b | 8.192 | sem resposta final | 8.572 | sem resposta final |
| qwen3:14b | 8.192 | sem resposta final | 10.137 | sem resposta final |
| gpt-oss:20b | 8.074 | sem resposta final | 8.074 | resposta final incompleta |

Phi-4 e Qwen 2.5 inventaram outros marcadores no pedido 8.192. Em 16.384, recuperaram os três códigos reais. O contraste combina teto reportado e recuperação literal: é evidência operacional de tratamento de um prompt maior que 8 mil nesses dois modelos, não prova independente de seu contexto máximo ou de truncamento exato.

Qwen 3.5, Qwen 3 e GPT-OSS retornaram campo de raciocínio e consumiram 128 tokens de saída. `finish_reason=stop` não impediu saída vazia/incompleta. Isso não demonstra incapacidade de ler o contexto, nem autoriza aprovar a resposta. Os contadores de detalhe registraram zero tokens de reasoning apesar de haver `reasoning_content`; essa inconsistência foi preservada, não corrigida por inferência.

O texto inteiro cabe abaixo de 8.192 no tokenizer reportado do GPT-OSS. Portanto, o teste dele **não confirma** processamento acima de 8 mil, mesmo quando `num_ctx=16384` é enviado.

Latências aproximadas (8.192 / 16.384), incluindo carga: Phi-4 8,0/22,8 s; Qwen 2.5 16,8/15,9 s; Qwen 3.5 25,4/7,6 s; Qwen 3 15,8/8,9 s; GPT-OSS 41,5/13,3 s. Uma repetição e estado de carga diferentes impedem ranking confiável de velocidade.

## Condição adicional de saída

Tentativa separada: Qwen 3.5, contexto solicitado 16.384, mesmo prompt, saída 512. A primeira chamada retornou HTTP 200 com JSON `null`, expondo uma ausência de validação no script de sondagem. Foi acrescentada a checagem explícita do contrato. Uma única repetição retornou novamente HTTP 200/JSON `null` (1,26 s), registrada como falha, sem resposta final. A primeira falha está descrita aqui; a repetição está no JSON. Não se conhece a causa no servidor.

A listagem `/api/models` continuou HTTP 200. Isso distingue disponibilidade da listagem de funcionamento da geração dessa condição. O ramo foi encerrado; não foram executadas condições 512 para Qwen 3 ou GPT-OSS, nem tentativas aleatórias com outros parâmetros.

## Conclusão e próximo passo

1. **Há diferenças reais nas capacidades declaradas.** Os 8.192 atuais são uma solicitação da aplicação, não limite intrínseco de todos os modelos, nem mesmo do Phi-4 instalado.
2. **Phi-4 e Qwen 2.5 aceitaram um teste útil acima de 8 mil**, recuperando os três marcadores com pedido 16.384. Essa é a condição inicial mais comprovada nesta sondagem.
3. **Qwen 3.5 e os demais candidatos de raciocínio não são substituições transparentes.** É necessário estabilizar saída/raciocínio e investigar a resposta `null` antes dos controles RAG.
4. Contexto maior não resolve por si só escopo, relações incorretas ou falsas aprovações do verificador. O próximo experimento deve comparar os controles negativos/cobertura com Phi-4 e Qwen 2.5, mantendo contexto e orçamento iguais; uma comparação de orçamento deve ficar separada.

Resultados exploratórios, sem conclusão de superioridade ou qualidade de produção. Reprodutor: `scripts/probe_cumbuco_context.py`; compilação e `git diff --check` passaram. O script modifica apenas seu arquivo de resultados; não altera providers/configuração.
