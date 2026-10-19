# Auditoria do chat: da pergunta à resposta com fontes

Data: 19/10/2026. Auditoria executada sem refatorar a aplicação, sem alterar configurações e sem novas chamadas à Spark.

**Conclusão:** há falhas reais de persistência e UX de fontes, além da conexão Spark ainda não integrada. Duplicação de responsabilidade existe, mas o teste de envio normal não demonstrou chamada duplicada no rerun.

## O que foi executado

134 testes passaram: 27 caracterizações novas e 107 testes existentes. As caracterizações também verificam defeitos atuais de propósito; verde não significa corrigido.

Comando reproduzível:

```bash
.venv/bin/python -m pytest tests/test_streamlit_chat_audit.py tests/test_runtime_config.py tests/test_vllm_provider.py tests/test_rag_v2_flow.py tests/test_rag_v2_sources_cache.py tests/test_shared_local_state.py tests/test_model_options.py tests/test_llm_client.py -q
```

A fixture chama a toolbar, Chat.show, normalização, render de fontes e persistência reais; substitui somente RAG e entradas de configuração, usa arquivos temporários e proíbe rede nos novos testes. Não chama o modelo nem o retriever. As sessões reais e a coleção institucional não são usadas como massa de teste.

## Caminho atual

```text
TOML + ambiente → RuntimeConfig / ModelOptions → seletor
chat persistido ↔ session_state → Chat.show
envio → últimas 6 mensagens → RAGService → RAGEngine / RAGFlow
RAGFlow → AgentTeam → ProviderRegistry → HTTP/modelo
resultado → status pronto → fontes renderizadas → mensagem normalizada → JSON
rerun → histórico restaurado → fontes renderizadas novamente
```

O cliente Spark LLMClient e o adaptador experimental não são o transporte escolhido automaticamente pelo Streamlit.

## Achados e prioridades

### F01 · P0 · Aplicação e cliente Spark não compartilham a configuração efetiva

**Evidência:** estático comprovado.

O perfil versionado da aplicação aponta para o endpoint local e Qwen 2.5, com overrides VLLM_*; preencher somente LLM_* não conecta o chat à Spark.

**Reprodução:** Seguir Chat → RAGService → RAGEngine → ProviderRegistry e comparar [llm] com o leitor LLMSettings. Nenhuma inferência real foi feita nesta auditoria.

**Correção proposta, não implementada:** Criar posteriormente um único resolvedor de configuração efetiva e um adaptador Spark na camada de providers, reutilizando transporte público com metadados. Não importar o runner do benchmark no frontend.

Testes: inspeção estática.

Código: [config/config.toml:5](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/config/config.toml:5), [application/service/rag/v2/Providers.py:285](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/service/rag/v2/Providers.py:285), [llm_client.py:43](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/llm_client.py:43).

### F02 · P1 · A autoridade do ambiente depende da ordem de inicialização

**Evidência:** reproduzido com ambiente sintético.

Um valor definido no processo vence no cliente isolado, mas pode ser sobrescrito pelo .env quando o bootstrap da aplicação roda.

**Reprodução:** Processo define process-model; arquivo temporário define file-model; LLMSettings retorna process-model antes e file-model depois do bootstrap.

**Correção proposta, não implementada:** Definir uma única precedência explícita. TOML como configuração normal; ambiente como override de implantação documentado; .env fornece segredos e compatibilidade transitória. Não sobrescrever os.environ como efeito colateral da leitura de configuração.

Testes: test_environment_authority_changes_after_application_bootstrap.

Código: [application/service/RuntimeConfig.py:36](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/service/RuntimeConfig.py:36), [llm_client.py:54](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/llm_client.py:54).

### F03 · P1 · Uma aba antiga pode sobrescrever mensagens mais recentes

**Evidência:** reproduzido em duas sessões AppTest.

O arquivo é gravado atomicamente, mas contém um snapshot completo desatualizado. Uma aba sem nova pergunta pode apagar do disco uma atualização da outra.

**Reprodução:** Abrir duas sessões isoladas; enviar nova mensagem na primeira; executar rerun na segunda. A mensagem nova desaparece do JSON temporário.

**Correção proposta, não implementada:** Persistir mutações por conversa, sem gravar em um render sem alteração. Introduzir revisão do snapshot e rejeitar conflito de gravação; conflito ou falha de armazenamento não deve repetir a geração. Preservar a política atual de histórico compartilhado; não introduzir autenticação nesta etapa.

Testes: test_two_sessions_overwrite_a_newer_snapshot.

Código: [application/presentation/chat_sessions/State.py:88](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat_sessions/State.py:88), [application/presentation/chat_sessions/Storage.py:68](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat_sessions/Storage.py:68).

### F04 · P1 · Falhas viram mensagens do assistente enviadas ao modelo

**Evidência:** reproduzido no fluxo normal com erro simulado.

A mensagem genérica de erro é salva como fala do assistente e integra as seis mensagens enviadas na pergunta seguinte.

**Reprodução:** Simular timeout; enviar outra pergunta bem-sucedida; inspecionar o histórico recebido pelo RAG simulado.

**Correção proposta, não implementada:** Separar conteúdo conversacional de estado operacional do turno. Exibir o erro sem incluí-lo como resposta factual no próximo prompt. A pergunta já aceita e o resultado remoto desconhecido precisam de identidade e estado próprios.

Testes: test_error_is_not_retried_but_becomes_semantic_history.

Código: [application/presentation/chat/Chat.py:452](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:452), [application/presentation/chat/Chat.py:530](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:530).

### F05 · P1 · O excerto completo perde seu estado ao marcar a opção

**Evidência:** reproduzido no caminho normal de fontes válidas.

A chave do checkbox inclui id(source), que muda quando mensagens são clonadas. Ao clicar, o rerun cria uma chave nova e a opção volta a desmarcada.

**Reprodução:** Gerar resposta sintética com fonte válida; marcar Ver excerto completo; conferir que a chave mudou e o valor voltou a falso.

**Correção proposta, não implementada:** Usar chaves estáveis ligadas ao turno e à identidade documental, sem id de objetos em memória. A mesma identidade deve governar fonte, destaque e preview.

Testes: test_source_expander_checkbox_key_changes_after_rerun.

Código: [application/presentation/chat/Chat.py:258](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:258), [application/presentation/chat_sessions/Normalization.py:110](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat_sessions/Normalization.py:110).

### F06 · P1 · Uma resposta pronta pode não estar salva, sem aviso ao usuário

**Evidência:** reproduzido com falha de armazenamento.

A geração conclui, mas erro de gravação é apenas registrado em warning. A resposta fica na memória enquanto o arquivo conserva a versão anterior.

**Reprodução:** Após inicializar uma sessão temporária, fazer a escrita falhar e enviar uma pergunta. A resposta aparece; o arquivo não muda; nenhum erro de armazenamento aparece na interface.

**Correção proposta, não implementada:** Retornar resultado da persistência à coordenação do turno; avisar que a resposta não foi salva e permitir repetir apenas a gravação, sem repetir o RAG.

Testes: test_persistence_failure_is_not_shown_to_user.

Código: [application/presentation/chat_sessions/Storage.py:59](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat_sessions/Storage.py:59), [application/presentation/chat/Chat.py:498](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:498).

### F07 · P2 · Fontes malformadas podem quebrar a tela depois de Resposta pronta

**Evidência:** reproduzido por injeção de resultado inválido.

provenance=[None] causa erro no render. O serviço simulado já devolveu a resposta e o status foi concluído, mas a mensagem do assistente não chega a ser persistida.

**Reprodução:** Injetar uma fonte malformada em cited_sources e enviar uma pergunta. Não se comprovou que o RAG V2 normal produza esse formato.

**Correção proposta, não implementada:** Validar e normalizar uma única vez o contrato de fontes na fronteira do resultado e da leitura de histórico. Render deve falhar de forma localizada e visível, preservando resposta e fontes válidas.

Testes: test_malformed_source_crashes_after_ready_status.

Código: [application/presentation/chat/Chat.py:240](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:240), [application/presentation/chat/Chat.py:227](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:227).

### F08 · P2 · Fontes e destaques inconsistentes são aceitos na apresentação

**Evidência:** reproduzido por injeção de dados inválidos.

A UI rotula E999 como Fonte citada mesmo sem E999 em evidence. Também destaca Atlas quando o campo quote diz Aurora, se os offsets estão dentro do tamanho do excerto.

**Reprodução:** Injetar identidade documental estranha à evidência ou offsets que não correspondem ao quote. O backend normal possui verificações; a lacuna é na restauração/fronteira de apresentação.

**Correção proposta, não implementada:** Verificar relações entre IDs e igualdade literal dos destaques em um contrato compartilhado. A interface não deve fazer nova avaliação semântica; deve consumir somente os dados documentais validados.

Testes: test_unknown_source_id_is_rendered_as_cited, test_mismatched_focus_quote_highlights_other_text.

Código: [application/presentation/chat/Chat.py:185](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:185), [application/service/rag/v2/Sources.py:12](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/service/rag/v2/Sources.py:12), [application/presentation/chat_sessions/Normalization.py:74](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat_sessions/Normalization.py:74).

### F09 · P2 · Objetos duplicados de fonte podem colidir nas chaves de widgets

**Evidência:** reproduzido por injeção; não observado no RAG normal.

Duas cópias distintas da mesma fonte geram duplicação visual; repetir a mesma instância de objeto causa StreamlitDuplicateElementKey.

**Reprodução:** Injetar cited_sources=[fonte,fonte] e depois duas cópias independentes. O Engine normalmente deduplica IDs antes de montar cited_sources.

**Correção proposta, não implementada:** Canonizar fontes por identidade estável e preservar associação com claims; aplicar a mesma normalização ao resultado novo e ao histórico.

Testes: test_duplicate_source_is_not_deduplicated, test_shared_duplicate_source_object_collides_in_widget_keys.

Código: [application/presentation/chat/Chat.py:258](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:258), [application/service/rag/v2/Engine.py:167](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/service/rag/v2/Engine.py:167).

### F10 · P2 · Mudança de configuração pode deixar serviço e seletor com valores antigos

**Evidência:** cache reproduzido; perfil alterado simulado.

RuntimeConfig é cacheado e o serviço fica em session_state. A invalidação observa nome do modelo e coleção, sem uma identidade do perfil de endpoint/configuração.

**Reprodução:** Mudar o endpoint sintético e enviar outra pergunta: a instância anterior permanece. Alterar o documento de configuração em memória: get_runtime_config mantém o valor antigo.

**Correção proposta, não implementada:** Definir contrato explícito de recarga. Inicialmente exigir reinício controlado ao mudar perfil; posteriormente invalidar por fingerprint de configuração no início de um novo turno, sem trocar parâmetros durante um turno em andamento.

Testes: test_profile_change_reuses_stale_service, test_runtime_config_cache_does_not_reload_toml_automatically.

Código: [application/service/RuntimeConfig.py:48](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/service/RuntimeConfig.py:48), [application/presentation/chat/Chat.py:398](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:398), [application/presentation/chat/Chat.py:425](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:425).

### F11 · P2 · Uma resposta não tem vínculo persistido com o turno e perfil de origem

**Evidência:** risco demonstrado por mutação de estado injetada.

Se o chat ativo muda durante a chamada, o código posterior escreve no chat agora ativo. O resultado também não persiste a identidade do modelo/coleção usados por mensagem.

**Reprodução:** Durante ask simulado, trocar chat ativo ou seleção. O teste evidencia ausência de vínculo; não simula fielmente interrupção/concor­rência do servidor Streamlit.

**Correção proposta, não implementada:** Capturar chat_id, turn_id, perfil, coleção e histórico ao aceitar o envio. Persistir o resultado no chat de origem. Testar interrupção e retomada reais antes de adotar processamento em background.

Testes: test_mutated_active_chat_receives_late_result_risk_injection, test_mutated_selection_does_not_bind_result_to_original_profile.

Código: [application/presentation/chat/Chat.py:486](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:486), [application/presentation/chat/Chat.py:457](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:457).

### F12 · P2 · Resposta vazia e configuração desconhecida não têm validação uniforme

**Evidência:** reproduzido nas fronteiras com dublê e configuração inválida.

Uma resposta vazia do serviço é marcada pronta. Um provider desconhecido passa por load_settings e só falha na resolução do provider.

**Reprodução:** Simular answer_text vazio; separadamente carregar provider inválido. Isso não prova que o transporte normal, que rejeita conteúdo vazio, entregue uma resposta vazia.

**Correção proposta, não implementada:** Validar o perfil no carregamento e o TurnResult antes de anunciar conclusão. Não usar conteúdo vazio para representar abstenção ou esclarecimento; esses são estados explícitos.

Testes: test_empty_answer_is_marked_complete_and_persisted, test_invalid_runtime_configuration_is_not_validated_at_settings_load.

Código: [application/presentation/chat/Chat.py:487](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/presentation/chat/Chat.py:487), [application/service/rag/v2/Config.py:7](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/service/rag/v2/Config.py:7), [application/service/rag/v2/Providers.py:438](/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/application/service/rag/v2/Providers.py:438).

## Matriz de configuração proposta

A centralização abaixo é uma proposta; nenhum valor foi migrado. Segredos continuam fora do TOML.

| Opção | Origem atual | Consumidor | Autoridade proposta | Compatibilidade |
|---|---|---|---|---|
| Modelo e provider da aplicação | [llm] | RAGService / ProviderRegistry / ModelOptions | Manter [llm] como autoridade | Preservar modelos salvos por turno; modelo antigo indisponível deve ter aviso, não troca silenciosa de identidade histórica. |
| Endpoint e autenticação Spark | [llm.providers.vllm] + VLLM_* versus LLM_* no cliente | Providers / LLMClient / adaptador no benchmark | Propor [llm.providers.spark], credencial referenciada por nome de variável | Não renomear variáveis nem alterar .env nesta auditoria. Migração posterior deve aceitar compatibilidade explicitamente e avisar conflitos. |
| LLM_BASE_URL / LLM_MODEL atuais | Ambiente/.env e defaults em llm_client.py | Cliente e check_llm | Valores normais no TOML; overrides de implantação explícitos | Durante transição, overrides não podem vencer silenciosamente outra autoridade. Documentar origem efetiva; não mostrar chave. |
| Thinking e sampling | Configuração de benchmark explícita; app pode herdar defaults do servidor | Payload do provider | Perfil explícito da aplicação, separado do benchmark | Qwen 3.6 precisa de thinking explícito; parâmetros do experimento não devem ser herdados implicitamente. |
| Janela e saída por papel | [llm] e defaults de LLMConfig; benchmark tem perfil distinto | AgentTeam / Providers | Manter limites por papel no perfil da aplicação e conferir entrada com tokenizer do gerador | Não trocar todos os papéis para 4096 nem confundir 3000 BGE com janela Qwen. Validar cada papel com a Spark posteriormente. |
| Orçamento documental | [rag_v2].context_tokens=3000; experimento muda pack_order para 6000 | RAGFlow versus InvestigationController | Manter 3000 na aplicação; perfis experimentais separados | Não promover 6000 nem trocar o controlador nesta etapa. |
| Histórico enviado | messages[-6:] literal em Chat.py | Submissão ao RAG | Propor [streamlit.chat].history_messages=6 | Preservar o tamanho padrão, mas separar avisos operacionais de conteúdo semântico em correção posterior. |
| Máximo de chats e título padrão | Constants.py: 6 e Nova conversa | Operações de chat | Propor [streamlit.chat].max_sessions=6 e default_title | Definir o que ocorre se limite novo for menor que o histórico existente; não excluir conversas. |
| Título curto | Normalization.truncate_title: 34 caracteres | Títulos automáticos/manuais | Propor [streamlit.chat].title_max_chars=34 | Default mantém comportamento; normalização em um único lugar. |
| Caminho e política do histórico | Constants.py: data/local_chat_sessions.json; armazenamento compartilhado | Storage | Propor [streamlit.history].path; política compartilhada explícita | Não mudar para histórico privado por usuário nem migrar banco automaticamente; preservar formato antigo ao adicionar revisão. |
| Modelo escolhido por conversa | JSON do chat + session_state + widget | Toolbar / State / Chat.show | Seleção por conversa sobre perfil validado; snapshot por turno | Não duplicar lista/modelo padrão em seção Streamlit. |
| Título e layout da página | set_page_config em application/app.py | Bootstrap da interface | Propor [streamlit.page] para título/layout | Aplicar antes de renderizar; não incluir regras de negócio em CSS. |
| Tema e paleta | Theme.py + SessionState.dark + .streamlit/config.toml | CSS próprio e widgets nativos | Uma referência de tema proposta; manter tokens visuais em camada de tema | Framework nativo não lê config/config.toml automaticamente; launcher deve passar opções nativas mapeadas, sem regravar arquivo no início de cada sessão. |
| Opções nativas de servidor | Defaults/CLI/env STREAMLIT_* e .streamlit/config.toml | Servidor Streamlit | Se centralizadas no projeto, launcher traduz campos permitidos para flags nativas | Preservar precedência CLI explícita de implantação e opções de segurança. Não aplicar server.* via chamadas tardias da página. |
| Excerto e progresso | 900 caracteres em Chat.py; mapas e defaults de status na apresentação | Fontes / status | Configurar apenas limites de produto; textos e CSS ficam na apresentação | Remover o mapa de progresso inicial sobrescrito, se confirmado sem uso; não mover toda string para TOML. |
| Perfis e assinaturas experimentais | [benchmark.*], hash do TOML inteiro e implementação | Runners históricos | Preservar sem alteração; futura mudança exige versão/assinatura nova | Mesmo alteração só de interface pode invalidar retomada antiga. Usar snapshots históricos; não flexibilizar checks para forçar compatibilidade. |

## Inventário de duplicações

- **RuntimeConfig e LLMSettings — lógica concorrente:** Precedências diferentes e modelo/URL em autoridades distintas. Unificar resolução de configuração; manter segredo fora do objeto público.
- **Providers e SparkProvider do benchmark — compatibilidade com política experimental distinta:** O adaptador experimental reutiliza payload do provider, mas acessa client._sdk e aplica guardas próprias. Extrair futuramente transporte público com metadados, mantendo retries e políticas de benchmark explicitamente separados.
- **Chat.show — responsabilidades sobrepostas:** Render, criação do serviço, execução, fontes e persistência no mesmo método; troca de modelo em dois caminhos. O teste de troca simples fez somente uma atualização. Não afirmar chamada duplicada já comprovada; separar coordenação do turno da renderização.
- **Sources / Normalization / montagem da mensagem — compatibilidade necessária e validação dispersa:** Compatibilidade sources/cited_sources existe e vazio autoritativo está correto; cópia não valida vínculo e formatos. Evoluir a fronteira existente em vez de criar um segundo normalizador semântico na UI.
- **SessionState / State / Operations / Storage — lógica concorrente de estado:** Mensagens e seleção são copiadas entre chat ativo, session_state e disco; initialize também persiste. Um repositório controla mutações persistentes, UI mantém seleção efêmera e turno captura origem.
- **RAGFlow e InvestigationController — fluxos distintos intencionalmente:** Um produz resposta e verificação; o outro investiga contexto com orçamento de decisões. Não fundir para reduzir linhas. A adoção experimental requer contrato de resposta e avaliação próprios.
- **Tema nativo e CSS da aplicação — camadas necessárias com defaults duplicados:** Há mecanismos diferentes e cores/defaults sobrepostos. Compartilhar referência de tema, preservando fronteira de configuração do servidor.

## Contratos e responsáveis propostos

- **Interface:** Selecionar chat/modelo/coleção, aceitar envio e renderizar estados/fontes já validados. Sem transporte HTTP, seleção de evidência ou gravação direta de snapshots durante render.
- **Coordenação do turno:** Capturar identidade de envio e perfil; executar RAG uma vez por submissão; associar resultado ao chat de origem. Uma execução pode conter várias chamadas de agentes. Rerun não é novo envio.
- **Configuração:** Resolver e validar um perfil efetivo, sem segredos expostos; controlar recarga/invalidação. Não depender da ordem de imports ou ler defaults conflitantes em cada consumidor.
- **RAG / transporte:** RAG decide recuperação, resposta e verificação; provider monta payload e transporte realiza chamada contabilizada. Retry HTTP, reparo JSON e feedback de investigação têm contagens e limites separados.
- **Contrato de resultado e fontes:** Validar status, IDs, campos e destaques literais; preservar cited_sources vazio e versão. Não reavaliar verdade semântica na UI; metadados inválidos não devem derrubar a conversa inteira.
- **Persistência:** Gravar mutações com revisão/conflito e informar resultado de gravação; restaurar formato validado. Não repetir geração após erro de disco; manter política compartilhada explicitada.

## Como interpretar chamadas

Uma pergunta aceita inicia uma execução do RAG, não uma única chamada HTTP. O RAGFlow usa vários papéis. ProviderRegistry.structured permite até duas tentativas de validação/reparo por chamada estruturada, enquanto AgentTeam usa max_retry_limit=0. LLMClient possui sua própria política de 429/5xx; o adaptador experimental usa max_retries=0. São mecanismos distintos e não devem ser somados ou duplicados sem rastreio.

Não foi detectada duplicação de execução no envio normal ou num rerun sem nova submissão. Isso não prova idempotência diante de interrupção real, retry do navegador ou resultado remoto desconhecido; faltam identidade persistida do turno e testes reais dessas interrupções.

## Cenários cobertos e limites

Cobertos: envio, rerun, segunda submissão explícita igual, falha/timeout sem repetição automática, mensagens operacionais no histórico, mudança normal de modelo e coleção, perfil cacheado, mutação injetada de chat/modelo/coleção durante chamada, gravação falhando, duas sessões com snapshot desatualizado, fontes vazias/duplicadas/malformadas/inconsistentes/indisponíveis, destaque inválido, recarga de histórico e configuração inválida.

O preview de arquivo ausente exibe mensagem localizada ao tentar abrir o arquivo; continua rotulado como fonte citada no resumo. O teste não confunde esse tratamento existente com uma exceção de render por fonte malformada.

O armazenamento compartilhado entre sessões é comportamento existente e intencional. O defeito reproduzido é a perda de atualização, não a ausência de contas de usuário. Nenhuma migração para histórico privado foi proposta automaticamente.

## Ordem recomendada para correções posteriores

1. Conectar o perfil efetivo da aplicação à Spark, preservando RAGFlow e 3000 tokens.
2. Separar submissão/turno, estado operacional e persistência; impedir gravações de snapshots antigos.
3. Usar identidade estável nas fontes e validar o contrato único de resultado/histórico.
4. Centralizar limites operacionais da UI e definir ponte para configuração nativa e recarga.
5. Somente depois avaliar adoção do controlador experimental e geração final com ele.

## O que ainda precisa de validação real

- No real Spark inference or answer quality evaluation.
- The full production Page, sidebar imports/uploads, native authentication and real server interruption/concurrency were not exercised end to end.
- State-injection tests establish a missing origin contract, not proof that ordinary synchronous UI interactions interleave in that way.
- Malformed results demonstrate resilience gaps; current backend guards can prevent those shapes in ordinary operation.
- Production remains RAG V2 at 3000 document tokens; experimental feedback/6000 controller is not promoted.

Depois da integração, validar pelo frontend uma pergunta simples com fonte, uma pergunta dependente do histórico e uma sem suporte documental; conferir payload efetivo, contagem de tokens por papel, referências e erro de autenticação/conexão. Esses testes reais não foram executados nesta auditoria.

A centralização pode alterar o hash do config.toml inteiro e impedir retomadas antigas. Preservar snapshots e assinaturas históricas; não editar resultados e não enfraquecer verificações para contornar isso.

Artefatos: findings.json, configuration_matrix.json, duplications.json, tests.xml, environment.json, screenshots/ e preservation.json. Nenhuma promoção experimental, nova avaliação do benchmark ou reativação de monitor.
