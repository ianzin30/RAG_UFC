# Chat com a Spark: correções e validação

A aplicação está conectada ao Qwen3.6 e preparada para testes controlados. A qualidade documental ainda tem pendências. O controlador experimental continua separado.

## Configuração entregue

Por orientação posterior do usuário, a janela local passou a **16.384 tokens Qwen** e o contexto documental a **6.000 tokens BGE**. Os limites de saída por papel foram preservados. Esses números não alteram a configuração do servidor nem demonstram ganho de qualidade.

TOML organiza aplicação, recuperação, benchmark e interface. Segredos permanecem no ambiente/.env, sem reescrita. A leitura não sobrescreve os overrides do processo. Valores legados conflitantes bloqueiam a preparação. O launcher traduz as opções nativas, usa o cache local e exige reinício após mudanças de código/configuração.

## Correções realizadas

- Provider Spark reutiliza a interface pública do cliente SDK e preserva modelo, parâmetros, consumo, término e contagem de tentativas. JSON segue no prompt, validado localmente com até um reparo; response_format não é enviado e não existe fallback automático entre modos.
- Um turno é registrado antes da execução, captura conversa/perfil/histórico e bloqueia outra pergunta concorrente na mesma conversa. Rerun não é submissão. Falhas, perguntas incompletas e resultados desconhecidos ficam fora do próximo histórico semântico.
- O armazenamento aplica operações sobre o estado atual, com revisão, lock entre processos e troca atômica. Não grava snapshots ao renderizar. Falha de gravação mostra aviso e permite salvar novamente sem executar o RAG. A migração cria backup; corrupção bloqueia a operação.
- Fontes usam identidade estável por turno, deduplicação e validação de referências e destaques. Erros de metadados ficam localizados. Expansão e fontes sobrevivem à recarga. Excertos compactos seguem o limite configurado.
- Erros aparecem junto à pergunta de origem. Perfil antigo não é trocado silenciosamente. Respostas parciais, abstenção e esclarecimento são estados concluídos distintos. Progresso do RAG usa o contexto da sessão somente durante o callback.
- Foi corrigido o vínculo inicial de requisitos: rótulos inexistentes do planejador são vinculados aos requisitos canônicos do controlador. Vínculos já válidos são preservados; buscas posteriores continuam com rejeição estrita de IDs desconhecidos.
- A saída detalhada do console CrewAI foi silenciada na aplicação. A sanitização de erros foi limitada ao agente da aplicação, preservando as causas usadas pelo feedback experimental.

## Testes

**481 testes passaram**, sem falhas. Três integrações históricas ficaram fora desta execução porque exigem os snapshots congelados anteriores. Um teste adicional confirma que a referência antiga rejeita o novo orçamento da aplicação. Nenhuma verificação de assinatura foi relaxada.

A bateria cobre duas sessões e processos, submissão/rerun, concorrência, migração, corrupção, gravação falhando e repetição apenas da gravação, resultado desconhecido, perfil congelado, token guard, parâmetros do SDK, fontes inválidas/repetidas e persistência dos destaques. O arquivo tests.xml registra os resultados.

Comando executado:

```sh
.venv/bin/python -m pytest tests -q --tb=short \
  --deselect=tests/test_global_order_replay.py::test_real_offline_replay_is_reproducible_and_resumes_only_same_signature \
  --deselect=tests/test_document_budget_replay.py::test_real_experiment_is_offline_reproducible_and_keeps_current_window \
  --deselect=tests/test_document_budget_cycle.py::test_real_preflight_has_no_transport_and_checks_both_budgets
```

## Chamadas reais pela página

As submissões foram sequenciais, em histórico separado do habitual e com o corpus existente. A tabela final abaixo distingue conclusão operacional de qualidade documental.

| Pergunta | Estado final | Chamadas lógicas | Tentativas HTTP de completion | Fontes citadas |
|---|---|---:|---:|---:|
| Quem coordena o projeto RACK? | abstained | 6 | 6 | 0 |
| E qual é a instituição executora desse projeto? | answered | 6 | 6 | 2 |
| Qual é a cor preferida do coordenador do projeto RACK? | failed | 5 | 4 | 0 |

A pergunta documental terminou em abstenção no protocolo final. Isso é um resultado insuficiente para aquele caso conhecido, mesmo que o chat tenha concluído e salvo corretamente. As respostas com fontes de versões anteriores e o caso de continuação não autorizam afirmar melhora geral. Não foi aplicada regra especial para essas perguntas.

### Diagnósticos anteriores preservados

A primeira submissão com 8.192/3.000 foi bloqueada localmente: 9.392 tokens contados conservadoramente, mais saída e margem. A mudança para 16.384/6.000 foi autorizada pelo usuário.

O bloqueio refere-se àquela chamada específica; chamadas anteriores do mesmo turno podem ter ocorrido. A interface atual usa a expressão Esta chamada ao modelo não foi enviada para deixar isso claro.

Na etapa com esquema enviado também ao servidor, surgiram IDs iniciais inválidos, bloqueios conservadores de tamanho e um HTTP 500 no caso adicional sem suporte. Duas perguntas foram respondidas com fontes nessa etapa. O protocolo final usa JSON no prompt e validação local; não contamos o esquema duas vezes. A causa interna do HTTP 500 não foi confirmada com acesso ao servidor.

Cada tentativa, inclusive falhas, está em validation.json, com configuração, fingerprint do código, parâmetros, término, consumo e tempos. As versões de desenvolvimento não formam uma comparação controlada de qualidade. Os três casos finais podem ter fingerprints diferentes por causa de uma correção posterior restrita à sanitização de exceções; seus perfis individuais são preservados.

## Preservação e limitações

Os arquivos históricos protegidos foram conferidos por hash. A seção benchmark do TOML permaneceu idêntica à arquivada. O histórico habitual migrou para formato 2 com backup; suas mensagens foram preservadas. A validação real usou arquivos temporários separados. Um novo cache de índice foi produzido durante a preparação; o corpus não foi editado.

A montagem do prompt do RAG ainda precisa de investigação própria. O orçamento documental não limita sozinho instruções, contrato, fatos e operandos numéricos enviados ao modelo. Não houve promoção do controlador experimental, novo benchmark ou reativação de monitor.

## Rodar e reproduzir

```sh
.venv/bin/python run_streamlit.py
```

Guia: [chat_spark.md](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/docs/chat_spark.md). Testes visuais sintéticos: `.venv/bin/python -m streamlit run docs/analises/chat_spark_fixture.py --server.port=8519`.

Detalhes: validation.json, validation_signature.json, preservation.json, tests.xml, screenshots/ e manifesto de hashes. As capturas distinguem dados sintéticos e execução real.
