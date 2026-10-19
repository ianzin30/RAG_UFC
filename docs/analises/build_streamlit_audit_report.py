"""Build a source-linked audit report from isolated characterization results."""
from pathlib import Path
import sys,json,hashlib,xml.etree.ElementTree as ET,zipfile,html,re,platform
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'docs/analises/auditoria_streamlit_2026-10-19/run_01'
from benchmark.core import artifacts

def ref(path,needle):
 lines=(ROOT/path).read_text().splitlines()
 return {'path':path,'line':next(i for i,s in enumerate(lines,1) if needle in s),'needle':needle}

def finding(id,title,priority,kind,impact,reproduction,tests,references,proposal):
 return dict(id=id,title=title,priority=priority,evidence_class=kind,impact=impact,
  reproduction=reproduction,tests=tests,references=[ref(*r) for r in references],proposal=proposal)

CHAT='application/presentation/chat/Chat.py';STORAGE='application/presentation/chat_sessions/Storage.py';STATE='application/presentation/chat_sessions/State.py';PROV='application/service/rag/v2/Providers.py'
findings=[
 finding('F01','Aplicação e cliente Spark não compartilham a configuração efetiva','P0','estático comprovado',
 'O perfil versionado da aplicação aponta para o endpoint local e Qwen 2.5, com overrides VLLM_*; preencher somente LLM_* não conecta o chat à Spark.',
 'Seguir Chat → RAGService → RAGEngine → ProviderRegistry e comparar [llm] com o leitor LLMSettings. Nenhuma inferência real foi feita nesta auditoria.',[],
 [('config/config.toml','[llm]'),(PROV,'os.getenv("VLLM_BASE_URL")'),('llm_client.py','class LLMSettings')],
 'Criar posteriormente um único resolvedor de configuração efetiva e um adaptador Spark na camada de providers, reutilizando transporte público com metadados. Não importar o runner do benchmark no frontend.'),
 finding('F02','A autoridade do ambiente depende da ordem de inicialização','P1','reproduzido com ambiente sintético',
 'Um valor definido no processo vence no cliente isolado, mas pode ser sobrescrito pelo .env quando o bootstrap da aplicação roda.',
 'Processo define process-model; arquivo temporário define file-model; LLMSettings retorna process-model antes e file-model depois do bootstrap.',
 ['test_environment_authority_changes_after_application_bootstrap'],
 [('application/service/RuntimeConfig.py','load_dotenv(dotenv_path=ENV_FILE, override=True)'),('llm_client.py','os.environ.get(name, values.get(name))')],
 'Definir uma única precedência explícita. TOML como configuração normal; ambiente como override de implantação documentado; .env fornece segredos e compatibilidade transitória. Não sobrescrever os.environ como efeito colateral da leitura de configuração.'),
 finding('F03','Uma aba antiga pode sobrescrever mensagens mais recentes','P1','reproduzido em duas sessões AppTest',
 'O arquivo é gravado atomicamente, mas contém um snapshot completo desatualizado. Uma aba sem nova pergunta pode apagar do disco uma atualização da outra.',
 'Abrir duas sessões isoladas; enviar nova mensagem na primeira; executar rerun na segunda. A mensagem nova desaparece do JSON temporário.',
 ['test_two_sessions_overwrite_a_newer_snapshot'],
 [(STATE,'def initialize_chat_sessions'),(STORAGE,'def persist_chat_state')],
 'Persistir mutações por conversa, sem gravar em um render sem alteração. Introduzir revisão do snapshot e rejeitar conflito de gravação; conflito ou falha de armazenamento não deve repetir a geração. Preservar a política atual de histórico compartilhado; não introduzir autenticação nesta etapa.'),
 finding('F04','Falhas viram mensagens do assistente enviadas ao modelo','P1','reproduzido no fluxo normal com erro simulado',
 'A mensagem genérica de erro é salva como fala do assistente e integra as seis mensagens enviadas na pergunta seguinte.',
 'Simular timeout; enviar outra pergunta bem-sucedida; inspecionar o histórico recebido pelo RAG simulado.',
 ['test_error_is_not_retried_but_becomes_semantic_history'],
 [(CHAT,'recent_history ='),(CHAT,'elif answer_text:')],
 'Separar conteúdo conversacional de estado operacional do turno. Exibir o erro sem incluí-lo como resposta factual no próximo prompt. A pergunta já aceita e o resultado remoto desconhecido precisam de identidade e estado próprios.'),
 finding('F05','O excerto completo perde seu estado ao marcar a opção','P1','reproduzido no caminho normal de fontes válidas',
 'A chave do checkbox inclui id(source), que muda quando mensagens são clonadas. Ao clicar, o rerun cria uma chave nova e a opção volta a desmarcada.',
 'Gerar resposta sintética com fonte válida; marcar Ver excerto completo; conferir que a chave mudou e o valor voltou a falso.',
 ['test_source_expander_checkbox_key_changes_after_rerun'],
 [(CHAT,'source_key ='),('application/presentation/chat_sessions/Normalization.py','def clone_messages')],
 'Usar chaves estáveis ligadas ao turno e à identidade documental, sem id de objetos em memória. A mesma identidade deve governar fonte, destaque e preview.'),
 finding('F06','Uma resposta pronta pode não estar salva, sem aviso ao usuário','P1','reproduzido com falha de armazenamento',
 'A geração conclui, mas erro de gravação é apenas registrado em warning. A resposta fica na memória enquanto o arquivo conserva a versão anterior.',
 'Após inicializar uma sessão temporária, fazer a escrita falhar e enviar uma pergunta. A resposta aparece; o arquivo não muda; nenhum erro de armazenamento aparece na interface.',
 ['test_persistence_failure_is_not_shown_to_user'],
 [(STORAGE,'except Exception as exc:'),(CHAT,'status.update(label="Resposta pronta."')],
 'Retornar resultado da persistência à coordenação do turno; avisar que a resposta não foi salva e permitir repetir apenas a gravação, sem repetir o RAG.'),
 finding('F07','Fontes malformadas podem quebrar a tela depois de Resposta pronta','P2','reproduzido por injeção de resultado inválido',
 'provenance=[None] causa erro no render. O serviço simulado já devolveu a resposta e o status foi concluído, mas a mensagem do assistente não chega a ser persistida.',
 'Injetar uma fonte malformada em cited_sources e enviar uma pergunta. Não se comprovou que o RAG V2 normal produza esse formato.',
 ['test_malformed_source_crashes_after_ready_status'],
 [(CHAT,'for item in source.get("provenance", [])'),(CHAT,'render_sources(sources)')],
 'Validar e normalizar uma única vez o contrato de fontes na fronteira do resultado e da leitura de histórico. Render deve falhar de forma localizada e visível, preservando resposta e fontes válidas.'),
 finding('F08','Fontes e destaques inconsistentes são aceitos na apresentação','P2','reproduzido por injeção de dados inválidos',
 'A UI rotula E999 como Fonte citada mesmo sem E999 em evidence. Também destaca Atlas quando o campo quote diz Aurora, se os offsets estão dentro do tamanho do excerto.',
 'Injetar identidade documental estranha à evidência ou offsets que não correspondem ao quote. O backend normal possui verificações; a lacuna é na restauração/fronteira de apresentação.',
 ['test_unknown_source_id_is_rendered_as_cited','test_mismatched_focus_quote_highlights_other_text'],
 [(CHAT,'def _valid_focus_spans'),('application/service/rag/v2/Sources.py','def preserve_v2_fields'),('application/presentation/chat_sessions/Normalization.py','preserve_v2_fields(message, normalized_message)')],
 'Verificar relações entre IDs e igualdade literal dos destaques em um contrato compartilhado. A interface não deve fazer nova avaliação semântica; deve consumir somente os dados documentais validados.'),
 finding('F09','Objetos duplicados de fonte podem colidir nas chaves de widgets','P2','reproduzido por injeção; não observado no RAG normal',
 'Duas cópias distintas da mesma fonte geram duplicação visual; repetir a mesma instância de objeto causa StreamlitDuplicateElementKey.',
 'Injetar cited_sources=[fonte,fonte] e depois duas cópias independentes. O Engine normalmente deduplica IDs antes de montar cited_sources.',
 ['test_duplicate_source_is_not_deduplicated','test_shared_duplicate_source_object_collides_in_widget_keys'],
 [(CHAT,'source_key ='),('application/service/rag/v2/Engine.py','ordered_ids =')],
 'Canonizar fontes por identidade estável e preservar associação com claims; aplicar a mesma normalização ao resultado novo e ao histórico.'),
 finding('F10','Mudança de configuração pode deixar serviço e seletor com valores antigos','P2','cache reproduzido; perfil alterado simulado',
 'RuntimeConfig é cacheado e o serviço fica em session_state. A invalidação observa nome do modelo e coleção, sem uma identidade do perfil de endpoint/configuração.',
 'Mudar o endpoint sintético e enviar outra pergunta: a instância anterior permanece. Alterar o documento de configuração em memória: get_runtime_config mantém o valor antigo.',
 ['test_profile_change_reuses_stale_service','test_runtime_config_cache_does_not_reload_toml_automatically'],
 [('application/service/RuntimeConfig.py','@lru_cache'),(CHAT,'collection_changed ='),(CHAT,'elif model_changed:')],
 'Definir contrato explícito de recarga. Inicialmente exigir reinício controlado ao mudar perfil; posteriormente invalidar por fingerprint de configuração no início de um novo turno, sem trocar parâmetros durante um turno em andamento.'),
 finding('F11','Uma resposta não tem vínculo persistido com o turno e perfil de origem','P2','risco demonstrado por mutação de estado injetada',
 'Se o chat ativo muda durante a chamada, o código posterior escreve no chat agora ativo. O resultado também não persiste a identidade do modelo/coleção usados por mensagem.',
 'Durante ask simulado, trocar chat ativo ou seleção. O teste evidencia ausência de vínculo; não simula fielmente interrupção/concor­rência do servidor Streamlit.',
 ['test_mutated_active_chat_receives_late_result_risk_injection','test_mutated_selection_does_not_bind_result_to_original_profile'],
 [(CHAT,'answer_trace = rag_service.ask_question_with_trace'),(CHAT,'chat_sessions.update_active_chat_messages(st.session_state.messages)')],
 'Capturar chat_id, turn_id, perfil, coleção e histórico ao aceitar o envio. Persistir o resultado no chat de origem. Testar interrupção e retomada reais antes de adotar processamento em background.'),
 finding('F12','Resposta vazia e configuração desconhecida não têm validação uniforme','P2','reproduzido nas fronteiras com dublê e configuração inválida',
 'Uma resposta vazia do serviço é marcada pronta. Um provider desconhecido passa por load_settings e só falha na resolução do provider.',
 'Simular answer_text vazio; separadamente carregar provider inválido. Isso não prova que o transporte normal, que rejeita conteúdo vazio, entregue uma resposta vazia.',
 ['test_empty_answer_is_marked_complete_and_persisted','test_invalid_runtime_configuration_is_not_validated_at_settings_load'],
 [(CHAT,'answer_text = str(answer_trace.get'),('application/service/rag/v2/Config.py','class ModelSelection'),(PROV,'Unknown provider')],
 'Validar o perfil no carregamento e o TurnResult antes de anunciar conclusão. Não usar conteúdo vazio para representar abstenção ou esclarecimento; esses são estados explícitos.'),
]
config=[
 ['Modelo e provider da aplicação','[llm]','RAGService / ProviderRegistry / ModelOptions','Manter [llm] como autoridade','Preservar modelos salvos por turno; modelo antigo indisponível deve ter aviso, não troca silenciosa de identidade histórica.'],
 ['Endpoint e autenticação Spark','[llm.providers.vllm] + VLLM_* versus LLM_* no cliente','Providers / LLMClient / adaptador no benchmark','Propor [llm.providers.spark], credencial referenciada por nome de variável','Não renomear variáveis nem alterar .env nesta auditoria. Migração posterior deve aceitar compatibilidade explicitamente e avisar conflitos.'],
 ['LLM_BASE_URL / LLM_MODEL atuais','Ambiente/.env e defaults em llm_client.py','Cliente e check_llm','Valores normais no TOML; overrides de implantação explícitos','Durante transição, overrides não podem vencer silenciosamente outra autoridade. Documentar origem efetiva; não mostrar chave.'],
 ['Thinking e sampling','Configuração de benchmark explícita; app pode herdar defaults do servidor','Payload do provider','Perfil explícito da aplicação, separado do benchmark','Qwen 3.6 precisa de thinking explícito; parâmetros do experimento não devem ser herdados implicitamente.'],
 ['Janela e saída por papel','[llm] e defaults de LLMConfig; benchmark tem perfil distinto','AgentTeam / Providers','Manter limites por papel no perfil da aplicação e conferir entrada com tokenizer do gerador','Não trocar todos os papéis para 4096 nem confundir 3000 BGE com janela Qwen. Validar cada papel com a Spark posteriormente.'],
 ['Orçamento documental','[rag_v2].context_tokens=3000; experimento muda pack_order para 6000','RAGFlow versus InvestigationController','Manter 3000 na aplicação; perfis experimentais separados','Não promover 6000 nem trocar o controlador nesta etapa.'],
 ['Histórico enviado','messages[-6:] literal em Chat.py','Submissão ao RAG','Propor [streamlit.chat].history_messages=6','Preservar o tamanho padrão, mas separar avisos operacionais de conteúdo semântico em correção posterior.'],
 ['Máximo de chats e título padrão','Constants.py: 6 e Nova conversa','Operações de chat','Propor [streamlit.chat].max_sessions=6 e default_title','Definir o que ocorre se limite novo for menor que o histórico existente; não excluir conversas.'],
 ['Título curto','Normalization.truncate_title: 34 caracteres','Títulos automáticos/manuais','Propor [streamlit.chat].title_max_chars=34','Default mantém comportamento; normalização em um único lugar.'],
 ['Caminho e política do histórico','Constants.py: data/local_chat_sessions.json; armazenamento compartilhado','Storage','Propor [streamlit.history].path; política compartilhada explícita','Não mudar para histórico privado por usuário nem migrar banco automaticamente; preservar formato antigo ao adicionar revisão.'],
 ['Modelo escolhido por conversa','JSON do chat + session_state + widget','Toolbar / State / Chat.show','Seleção por conversa sobre perfil validado; snapshot por turno','Não duplicar lista/modelo padrão em seção Streamlit.'],
 ['Título e layout da página','set_page_config em application/app.py','Bootstrap da interface','Propor [streamlit.page] para título/layout','Aplicar antes de renderizar; não incluir regras de negócio em CSS.'],
 ['Tema e paleta','Theme.py + SessionState.dark + .streamlit/config.toml','CSS próprio e widgets nativos','Uma referência de tema proposta; manter tokens visuais em camada de tema','Framework nativo não lê config/config.toml automaticamente; launcher deve passar opções nativas mapeadas, sem regravar arquivo no início de cada sessão.'],
 ['Opções nativas de servidor','Defaults/CLI/env STREAMLIT_* e .streamlit/config.toml','Servidor Streamlit','Se centralizadas no projeto, launcher traduz campos permitidos para flags nativas','Preservar precedência CLI explícita de implantação e opções de segurança. Não aplicar server.* via chamadas tardias da página.'],
 ['Excerto e progresso','900 caracteres em Chat.py; mapas e defaults de status na apresentação','Fontes / status','Configurar apenas limites de produto; textos e CSS ficam na apresentação','Remover o mapa de progresso inicial sobrescrito, se confirmado sem uso; não mover toda string para TOML.'],
 ['Perfis e assinaturas experimentais','[benchmark.*], hash do TOML inteiro e implementação','Runners históricos','Preservar sem alteração; futura mudança exige versão/assinatura nova','Mesmo alteração só de interface pode invalidar retomada antiga. Usar snapshots históricos; não flexibilizar checks para forçar compatibilidade.'],
]
dup=[
 {'area':'RuntimeConfig e LLMSettings','class':'lógica concorrente','finding':'Precedências diferentes e modelo/URL em autoridades distintas.','direction':'Unificar resolução de configuração; manter segredo fora do objeto público.'},
 {'area':'Providers e SparkProvider do benchmark','class':'compatibilidade com política experimental distinta','finding':'O adaptador experimental reutiliza payload do provider, mas acessa client._sdk e aplica guardas próprias.','direction':'Extrair futuramente transporte público com metadados, mantendo retries e políticas de benchmark explicitamente separados.'},
 {'area':'Chat.show','class':'responsabilidades sobrepostas','finding':'Render, criação do serviço, execução, fontes e persistência no mesmo método; troca de modelo em dois caminhos. O teste de troca simples fez somente uma atualização.','direction':'Não afirmar chamada duplicada já comprovada; separar coordenação do turno da renderização.'},
 {'area':'Sources / Normalization / montagem da mensagem','class':'compatibilidade necessária e validação dispersa','finding':'Compatibilidade sources/cited_sources existe e vazio autoritativo está correto; cópia não valida vínculo e formatos.','direction':'Evoluir a fronteira existente em vez de criar um segundo normalizador semântico na UI.'},
 {'area':'SessionState / State / Operations / Storage','class':'lógica concorrente de estado','finding':'Mensagens e seleção são copiadas entre chat ativo, session_state e disco; initialize também persiste.','direction':'Um repositório controla mutações persistentes, UI mantém seleção efêmera e turno captura origem.'},
 {'area':'RAGFlow e InvestigationController','class':'fluxos distintos intencionalmente','finding':'Um produz resposta e verificação; o outro investiga contexto com orçamento de decisões.','direction':'Não fundir para reduzir linhas. A adoção experimental requer contrato de resposta e avaliação próprios.'},
 {'area':'Tema nativo e CSS da aplicação','class':'camadas necessárias com defaults duplicados','finding':'Há mecanismos diferentes e cores/defaults sobrepostos.','direction':'Compartilhar referência de tema, preservando fronteira de configuração do servidor.'},
]
responsibilities=[
 ['Interface','Selecionar chat/modelo/coleção, aceitar envio e renderizar estados/fontes já validados.','Sem transporte HTTP, seleção de evidência ou gravação direta de snapshots durante render.'],
 ['Coordenação do turno','Capturar identidade de envio e perfil; executar RAG uma vez por submissão; associar resultado ao chat de origem.','Uma execução pode conter várias chamadas de agentes. Rerun não é novo envio.'],
 ['Configuração','Resolver e validar um perfil efetivo, sem segredos expostos; controlar recarga/invalidação.','Não depender da ordem de imports ou ler defaults conflitantes em cada consumidor.'],
 ['RAG / transporte','RAG decide recuperação, resposta e verificação; provider monta payload e transporte realiza chamada contabilizada.','Retry HTTP, reparo JSON e feedback de investigação têm contagens e limites separados.'],
 ['Contrato de resultado e fontes','Validar status, IDs, campos e destaques literais; preservar cited_sources vazio e versão.','Não reavaliar verdade semântica na UI; metadados inválidos não devem derrubar a conversa inteira.'],
 ['Persistência','Gravar mutações com revisão/conflito e informar resultado de gravação; restaurar formato validado.','Não repetir geração após erro de disco; manter política compartilhada explicitada.'],
]
rootxml=ET.parse(OUT/'tests.xml').getroot();testcases=list(rootxml.iter('testcase'))
newtests=[t for t in testcases if 'test_streamlit_chat_audit' in t.get('classname','')]
tests={'total':len(testcases),'audit_characterizations':len(newtests),'existing':len(testcases)-len(newtests),
 'failures':len(list(rootxml.iter('failure'))),'errors':len(list(rootxml.iter('error'))),
 'note':'Passing characterizations include assertions of current defects; they do not mean defects were fixed.',
 'test_names':[t.get('name') for t in newtests]}
assert tests['failures']==tests['errors']==0
result={'title':'Auditoria do chat: da pergunta à resposta com fontes','date':'2026-10-19',
 'production_changed':False,'new_model_calls':0,'new_retrieval_calls':0,'tests':tests,'findings':findings,
 'configuration_matrix':config,'duplication_inventory':dup,'responsibilities':responsibilities,
 'scope':'Real Chat.show, toolbar, sessions and JSON persistence under AppTest with fake RAG, temporary storage/documents and network guard. Real browser uses the same synthetic fixture.',
 'limitations':['No real Spark inference or answer quality evaluation.',
 'The full production Page, sidebar imports/uploads, native authentication and real server interruption/concurrency were not exercised end to end.',
 'State-injection tests establish a missing origin contract, not proof that ordinary synchronous UI interactions interleave in that way.',
 'Malformed results demonstrate resilience gaps; current backend guards can prevent those shapes in ordinary operation.',
 'Production remains RAG V2 at 3000 document tokens; experimental feedback/6000 controller is not promoted.'],
 'working_behaviors':['Normal submission: one flow execution; plain rerun: no second execution.',
 'Identical question explicitly submitted twice: two flow executions, correctly.',
 'Simple model change calls set_model once; collection change recreates service.',
 'Exceptions/timeouts do not automatically rerun the flow in the tested path.',
 'Callbacks are cleared after success and errors.',
 'Empty cited_sources remains authoritative, including after history reload.',
 'Valid evidence IDs and focus spans survive persistence reload.'],
 'next_order':['P0: integrate effective application profile and Spark transport, keeping RAGFlow and 3000 unchanged.',
 'P1: protect persistent conversations and turn lifecycle; separate operational failures and persistence errors.',
 'P1/P2: stabilize source widget identities; validate result/source boundaries and literal highlights.',
 'P2: improve status wording, profile reload contract and native configuration bridge.',
 'Only later: assess experimental controller and answer generation as separate intervention.']}
artifacts.save_json(OUT/'findings.json',result)
artifacts.save_json(OUT/'configuration_matrix.json',config)
artifacts.save_json(OUT/'duplications.json',dup)
lines=['# '+result['title'],'','Data: 19/10/2026. Auditoria executada sem refatorar a aplicação, sem alterar configurações e sem novas chamadas à Spark.','',
 '**Conclusão:** há falhas reais de persistência e UX de fontes, além da conexão Spark ainda não integrada. Duplicação de responsabilidade existe, mas o teste de envio normal não demonstrou chamada duplicada no rerun.','',
 '## O que foi executado','',f"{tests['total']} testes passaram: {tests['audit_characterizations']} caracterizações novas e {tests['existing']} testes existentes. As caracterizações também verificam defeitos atuais de propósito; verde não significa corrigido.",'',
 'Comando reproduzível:','', '```bash', '.venv/bin/python -m pytest tests/test_streamlit_chat_audit.py tests/test_runtime_config.py tests/test_vllm_provider.py tests/test_rag_v2_flow.py tests/test_rag_v2_sources_cache.py tests/test_shared_local_state.py tests/test_model_options.py tests/test_llm_client.py -q','```','',
 'A fixture chama a toolbar, Chat.show, normalização, render de fontes e persistência reais; substitui somente RAG e entradas de configuração, usa arquivos temporários e proíbe rede nos novos testes. Não chama o modelo nem o retriever. As sessões reais e a coleção institucional não são usadas como massa de teste.','',
 '## Caminho atual','', '```text','TOML + ambiente → RuntimeConfig / ModelOptions → seletor',
 'chat persistido ↔ session_state → Chat.show',
 'envio → últimas 6 mensagens → RAGService → RAGEngine / RAGFlow',
 'RAGFlow → AgentTeam → ProviderRegistry → HTTP/modelo',
 'resultado → status pronto → fontes renderizadas → mensagem normalizada → JSON',
 'rerun → histórico restaurado → fontes renderizadas novamente','```','',
 'O cliente Spark LLMClient e o adaptador experimental não são o transporte escolhido automaticamente pelo Streamlit.','',
 '## Achados e prioridades','']
for f in findings:
 lines += [f"### {f['id']} · {f['priority']} · {f['title']}",'',f"**Evidência:** {f['evidence_class']}.",'',f['impact'],'','**Reprodução:** '+f['reproduction'],'','**Correção proposta, não implementada:** '+f['proposal'],'',
 'Testes: '+(', '.join(f['tests']) or 'inspeção estática')+'.','',
 'Código: '+', '.join(f"[{r['path']}:{r['line']}]({ROOT/r['path']}:{r['line']})" for r in f['references'])+'.','']
lines += ['## Matriz de configuração proposta','','A centralização abaixo é uma proposta; nenhum valor foi migrado. Segredos continuam fora do TOML.','',
 '| Opção | Origem atual | Consumidor | Autoridade proposta | Compatibilidade |','|---|---|---|---|---|']
for row in config:lines.append('| '+' | '.join(row)+' |')
lines += ['','## Inventário de duplicações','']
for row in dup:lines += ['- **'+row['area']+' — '+row['class']+':** '+row['finding']+' '+row['direction']]
lines += ['','## Contratos e responsáveis propostos','']
for owner,role,boundary in responsibilities:lines+=['- **'+owner+':** '+role+' '+boundary]
lines += ['','## Como interpretar chamadas','',
 'Uma pergunta aceita inicia uma execução do RAG, não uma única chamada HTTP. O RAGFlow usa vários papéis. ProviderRegistry.structured permite até duas tentativas de validação/reparo por chamada estruturada, enquanto AgentTeam usa max_retry_limit=0. LLMClient possui sua própria política de 429/5xx; o adaptador experimental usa max_retries=0. São mecanismos distintos e não devem ser somados ou duplicados sem rastreio.',
 '', 'Não foi detectada duplicação de execução no envio normal ou num rerun sem nova submissão. Isso não prova idempotência diante de interrupção real, retry do navegador ou resultado remoto desconhecido; faltam identidade persistida do turno e testes reais dessas interrupções.','',
 '## Cenários cobertos e limites','',
 'Cobertos: envio, rerun, segunda submissão explícita igual, falha/timeout sem repetição automática, mensagens operacionais no histórico, mudança normal de modelo e coleção, perfil cacheado, mutação injetada de chat/modelo/coleção durante chamada, gravação falhando, duas sessões com snapshot desatualizado, fontes vazias/duplicadas/malformadas/inconsistentes/indisponíveis, destaque inválido, recarga de histórico e configuração inválida.', '',
 'O preview de arquivo ausente exibe mensagem localizada ao tentar abrir o arquivo; continua rotulado como fonte citada no resumo. O teste não confunde esse tratamento existente com uma exceção de render por fonte malformada.','',
 'O armazenamento compartilhado entre sessões é comportamento existente e intencional. O defeito reproduzido é a perda de atualização, não a ausência de contas de usuário. Nenhuma migração para histórico privado foi proposta automaticamente.','',
 '## Ordem recomendada para correções posteriores','']
lines += ['1. Conectar o perfil efetivo da aplicação à Spark, preservando RAGFlow e 3000 tokens.',
 '2. Separar submissão/turno, estado operacional e persistência; impedir gravações de snapshots antigos.',
 '3. Usar identidade estável nas fontes e validar o contrato único de resultado/histórico.',
 '4. Centralizar limites operacionais da UI e definir ponte para configuração nativa e recarga.',
 '5. Somente depois avaliar adoção do controlador experimental e geração final com ele.','',
 '## O que ainda precisa de validação real','']
lines += ['- '+limit for limit in result['limitations']]
lines += ['','Depois da integração, validar pelo frontend uma pergunta simples com fonte, uma pergunta dependente do histórico e uma sem suporte documental; conferir payload efetivo, contagem de tokens por papel, referências e erro de autenticação/conexão. Esses testes reais não foram executados nesta auditoria.','',
 'A centralização pode alterar o hash do config.toml inteiro e impedir retomadas antigas. Preservar snapshots e assinaturas históricas; não editar resultados e não enfraquecer verificações para contornar isso.','',
 'Artefatos: findings.json, configuration_matrix.json, duplications.json, tests.xml, environment.json, screenshots/ e preservation.json. Nenhuma promoção experimental, nova avaliação do benchmark ou reativação de monitor.']
(OUT/'relatorio.md').write_text('\n'.join(lines)+'\n')
# Visual report uses the existing explanation register, not production UI changes.
head='<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Auditoria do chat Streamlit</title>'
style=(ROOT/'docs/analises/streamlit_audit_report.css').read_text()
style+='''nav{display:flex;gap:1rem;flex-wrap:wrap;padding:1rem 0;border-bottom:1px solid var(--border)}.pipeline{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.pipeline>div{padding:1rem;border:1px solid var(--border)}.arrow-label{font-size:.875rem;color:var(--text-dim);display:block;margin-top:1rem}.cases{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.5rem}.cases>div{padding:1rem;border:1px solid var(--border)}.tag{font:500 .75rem var(--font-mono);display:inline-block;border:1px solid var(--border-bright);padding:.25rem .5rem;margin-bottom:1rem}.risk-text{color:var(--risk)}.table-scroll{overflow:auto}table{border-collapse:collapse;min-width:850px;text-align:left}th,td{padding:.75rem 1rem;border-bottom:1px solid var(--border);vertical-align:top}th{font-size:.875rem}details{padding:1rem 0;border-top:1px solid var(--border)}details p{max-width:68ch;margin-top:1rem}summary{cursor:pointer}img{max-width:100%;height:auto;border:1px solid var(--border)}.source-ref{font-size:.875rem;overflow-wrap:anywhere}.checks{display:flex;flex-wrap:wrap;gap:.5rem}.checks span{border:1px solid var(--border);padding:.5rem .75rem}@media(max-width:650px){.pipeline,.cases{grid-template-columns:minmax(0,1fr)}}'''
body=f'''<main><header><p class="muted">AUDITORIA ISOLADA · 19 OUT 2026</p><h1>O chat precisa de conexões mais claras.</h1><p class="intro">Há falhas reproduzidas no histórico e nas fontes. Não detectamos repetição da execução no envio normal testado. Nenhuma correção foi aplicada.</p></header><nav><a href="#path">Caminho atual</a><a href="#bugs">Problemas reproduzidos</a><a href="#config">Configuração</a><a href="#evidence">Testes e limites</a><a href="#next">Próximas correções</a></nav>
<figure><div class="scope"><div><h3>Comportamentos que funcionaram</h3><div class="step">Enviar pergunta → uma execução do RAG.</div><div class="step">Rerun sem novo envio → nenhuma execução extra.</div><div class="step">Fontes citadas vazias → continuam vazias após recarregar.</div></div><div><h3>Problemas encontrados</h3><div class="step">Outra aba pode sobrescrever mensagens novas.</div><div class="step">Erros entram no histórico enviado ao modelo.</div><div class="step">“Ver excerto completo” perde o estado no rerun.</div></div></div><figcaption>O teste usa a lógica real do chat com RAG simulado, documentos sintéticos e armazenamento temporário. A Spark não foi chamada.</figcaption></figure>
<section id="path"><h2>O caminho mistura apresentação e execução.</h2><figure><div class="pipeline"><div><strong>Configuração + seleção</strong><span class="arrow-label">Escolhem perfil e coleção →</span></div><div><strong>Chat.show</strong><span class="arrow-label">Prepara serviço, histórico e pergunta →</span></div><div><strong>RAG V2 + providers</strong><span class="arrow-label">Recuperam, geram e verificam →</span></div><div><strong>Resposta + fontes</strong><span class="arrow-label">Voltam à interface →</span></div><div><strong>Mensagem + JSON</strong><span class="arrow-label">São copiados e gravados →</span></div><div><strong>Rerun / outra aba</strong><span class="arrow-label">Restaura e pode gravar o snapshot novamente.</span></div></div><figcaption>A interface já exibe respostas e citações. Falta uma fronteira única para configuração efetiva, identidade do turno e persistência.</figcaption></figure></section>
<section id="bugs"><h2>Os problemas têm níveis diferentes de evidência.</h2><figure><div class="cases">'''
for id in ['F03','F04','F05','F06']:
 f=next(f for f in findings if f['id']==id)
 body+=f'<div><span class="tag">{f["id"]} · {f["priority"]} · reproduzido</span><h3>{html.escape(f["title"])}</h3><p>{html.escape(f["impact"])}</p></div>'
body+='</div><figcaption>Esses achados usam comportamento real da apresentação e do histórico. Serviços e falhas são simulados; os arquivos reais não participam do teste.</figcaption></figure>'
for f in findings:
 body+=f'<details><summary>{f["id"]} · {f["priority"]} · {html.escape(f["title"])}</summary><p><strong>{html.escape(f["evidence_class"])}</strong></p><p>{html.escape(f["impact"])}</p><p class="muted">Reprodução: {html.escape(f["reproduction"])}</p><p><strong>Proposta, ainda não implementada:</strong> {html.escape(f["proposal"])}</p><p class="source-ref">'
 body+=' · '.join(f'<a href="{(ROOT/r["path"]).as_uri()}#L{r["line"]}">{r["path"]}:{r["line"]}</a>' for r in f['references'])
 body+='</p></details>'
body+='''</section><section id="config"><h2>Um TOML pode organizar os perfis sem misturá-los.</h2><figure><div class="scope"><div><div class="step"><strong>Modelo da aplicação</strong><br>Provider, modelo, endpoint, janela e saída por papel.</div><div class="step"><strong>Recuperação</strong><br>Gemma, BGE, índice e contexto documental.</div><div class="step"><strong>Interface</strong><br>Limites de histórico, conversas e opções da página.</div></div><div><div class="step"><strong>Experimentos</strong><br>Perfis e assinaturas congelados, separados da aplicação.</div><div class="step"><strong>Segredos</strong><br>Continuam no ambiente; não entram no TOML público.</div><div class="step"><strong>Servidor Streamlit</strong><br>Precisa de ponte no launcher; não lê o TOML do projeto automaticamente.</div></div></div><figcaption>É uma proposta de autoridade. Nenhuma variável foi migrada e nenhum valor de produção foi alterado. Trocar o TOML pode afetar assinaturas antigas do benchmark.</figcaption></figure><details><summary>Matriz completa: origem, consumidor, autoridade e compatibilidade</summary><div class="table-scroll"><table><thead><tr><th>Opção</th><th>Origem atual</th><th>Consumidor</th><th>Autoridade proposta</th><th>Compatibilidade</th></tr></thead><tbody>'''
for row in config:body+='<tr>'+''.join('<td>'+html.escape(cell)+'</td>' for cell in row)+'</tr>'
body+='</tbody></table></div></details></section>'
body+=f'''<section id="evidence"><h2>Os testes reproduzem defeitos; não os corrigem.</h2><figure><div class="checks"><span>{tests['audit_characterizations']} caracterizações novas</span><span>{tests['existing']} testes existentes</span><span>{tests['total']} passaram</span><span>Zero chamadas reais ao modelo</span></div><p class="intro">Há um caminho básico funcionando. As falhas e os riscos foram documentados sem refatorar a aplicação.</p><figcaption>Dados inválidos e troca de estado durante chamada foram injetados. Não demonstram, por si só, que o backend normal gere esses dados ou que uma interação real interrompa o servidor do mesmo modo.</figcaption></figure><details><summary>Ver capturas da interface real com dados sintéticos</summary>'''
for file,label in [('01-ready.png','Preparação'),('02-progress.png','Pergunta em execução'),('03-response-sources.png','Resposta e fontes'),('04-generation-error.png','Erro simulado'),('06-source-preview.png','Preview do documento')]:
 if (OUT/'screenshots'/file).exists():body+=f'<p>{label}</p><img loading="lazy" src="{(OUT/"screenshots"/file).as_uri()}" alt="{label}: fixture isolada do Streamlit">'
body+='''</details></section><section id="next"><h2>Corrigir por fronteira, preservando o que funciona.</h2><figure><div class="pipeline"><div><strong>Conectar a Spark</strong><span class="arrow-label">Um perfil efetivo e um transporte público →</span></div><div><strong>Proteger o turno e o histórico</strong><span class="arrow-label">Identidade de origem, erros separados e gravação com conflito →</span></div><div><strong>Consolidar fontes e estados</strong><span class="arrow-label">IDs estáveis, contrato validado e UX previsível.</span></div></div><figcaption>O RAG V2 e os 3.000 tokens permanecem como base. Levar o agente experimental à interface exige uma etapa própria de resposta e avaliação.</figcaption></figure><p class="intro">Ainda falta integrar e testar perguntas reais pela Spark, além de interrupções reais do Streamlit. O relatório não apresenta os testes simulados como validação de ponta a ponta do modelo.</p></section><section class="sources"><h2>Inspecionar e reproduzir</h2><p>'''
body+=' · '.join(f'<a href="{(OUT/f).as_uri()}">{label}</a>' for f,label in [('relatorio.md','Relatório completo'),('findings.json','Achados e contratos'),('configuration_matrix.json','Matriz de configuração'),('duplications.json','Duplicações'),('tests.xml','Resultados dos testes'),('preservation.json','Preservação')])
body+='</p></section></main>'
page=head+'<style>'+style+'</style></head><body>'+body+'</body></html>'
for p in [Path.home()/'.agent/diagrams/auditoria_chat_streamlit_2026-10-19.html',ROOT/'docs/resultado_auditoria_chat_streamlit_2026-10-19.html']:
 p.write_text(page)
with zipfile.ZipFile(OUT/'audit_code.zip','w',zipfile.ZIP_DEFLATED) as z:
 for path in ['tests/test_streamlit_chat_audit.py','docs/analises/streamlit_audit_support.py','docs/analises/streamlit_audit_app.py','docs/analises/build_streamlit_audit_report.py','docs/analises/streamlit_audit_report.css']:
  z.write(ROOT/path,path)
print(json.dumps({'findings':len(findings),'config_options':len(config),'tests':{k:v for k,v in tests.items() if k!='test_names'}},ensure_ascii=False))
