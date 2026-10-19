"""Build the correction report without importing runtime services or credentials."""
from pathlib import Path
import json
import html
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/analises/correcao_chat_spark_2026-10-19'


def rows(path, phase):
    if not path.exists(): return []
    state=json.loads(path.read_text())
    result=[]
    for chat in state['chat_sessions']:
        messages=chat.get('messages',[])
        for turn in chat.get('turns',[]):
            identifier=turn['turn_id']
            user=next((m for m in messages if m.get('turn_id')==identifier and m.get('role')=='user'),{})
            answer=next((m for m in messages if m.get('turn_id')==identifier and m.get('role')=='assistant'),{})
            execution=turn.get('execution') or {}
            result.append({'phase':phase,'turn_id':identifier,'question':user.get('content'),'state':turn['state'],
                'error':turn.get('error'),'logical_calls':execution.get('logical_calls',0),'transport_attempts':execution.get('transport_attempts',0),
                'sources':len(answer.get('cited_sources',[])),
                'valid_focus_spans':sum(len(s.get('focus_spans',[])) for s in answer.get('cited_sources',[])),
                'provider_calls':execution.get('provider_calls',[]),'error_type':execution.get('error_type'),
                'error_origin':execution.get('error_origin'),
                'profile':turn.get('profile'),'collection':turn.get('collection'),
                'started_at':turn.get('created_at'),'finished_at':turn.get('finished_at')})
    for row in result:
        if row['error'] and row['error'].startswith('Entrada excede a janela local:') and row['logical_calls'] == 1 and all(not c.get('observed', {}).get('usage') and not c.get('server_timings') for c in row['provider_calls']):
            row['original_diagnostic_transport_count'] = row['transport_attempts']
            row['transport_attempts'] = 0
            row['diagnostic_correction'] = 'Early development counter defaulted to one even though the first request was blocked before transport. Original store was not modified.'
    return result


all_rows=rows(Path('/tmp/rag-spark-chat-validation-20261019.json'),'initial_8192_3000')
all_rows+=rows(Path('/tmp/rag-spark-chat-validation-20261019-16k.json'),'development_16384_6000')
final=rows(Path('/tmp/rag-spark-final-validation-20261019.json'),'final_protocol_16384_6000')
all_rows+=final
xml=ET.parse(OUT/'tests.xml').getroot()
tests={'passed':len(list(xml.iter('testcase')))-len(list(xml.iter('failure')))-len(list(xml.iter('error'))),
       'failures':len(list(xml.iter('failure'))),'errors':len(list(xml.iter('error'))),'deselected_frozen_integrations':3}
assert tests['failures']==tests['errors']==0
result={'title':'Chat com a Spark: correções e validação','tests':tests,'final_protocol_cases':final,
 'development_cases':[r for r in all_rows if r not in final],
 'costs':{'logical_calls':sum(r['logical_calls'] for r in all_rows),'completion_transport_attempts':sum(r['transport_attempts'] for r in all_rows)},
 'cost_scope':'Counts cover recorded turn completion requests only. Model-discovery GETs, retrieval preparation and CPU time are excluded. HTTP attempts are not GPU executions.',
 'limits':{'qwen_window':16384,'bge_document_context':6000,'thinking':False,'temperature':0,'seed':42},
 'no_experimental_controller_promotion':True,
 'interpretation':'Integration diagnostics across explicitly recorded development versions; not a paired quality experiment. Abstention is a completed response state, not proof of missing corpus evidence.',
 'remaining':['Known documentary question abstained in final prompt-JSON protocol although earlier server-schema development calls answered it. Retrieval/verification quality is not homologated.',
 'Development cases hit conservative input budget checks and HTTP 500; all attempts remain recorded. No automatic whole-RAG replay was used.',
 'Historical integration replays require original code/configuration snapshots; no signature check was relaxed.',
 'Tests and visual checks do not establish crash-safe remote exactly-once delivery or multi-host storage support.']}
(OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
lines=['# Chat com a Spark: correções e validação','',
 'A aplicação está conectada ao Qwen3.6 e preparada para testes controlados. A qualidade documental ainda tem pendências. O controlador experimental continua separado.','',
 '## Configuração entregue','',
 'Por orientação posterior do usuário, a janela local passou a **16.384 tokens Qwen** e o contexto documental a **6.000 tokens BGE**. Os limites de saída por papel foram preservados. Esses números não alteram a configuração do servidor nem demonstram ganho de qualidade.','',
 'TOML organiza aplicação, recuperação, benchmark e interface. Segredos permanecem no ambiente/.env, sem reescrita. A leitura não sobrescreve os overrides do processo. Valores legados conflitantes bloqueiam a preparação. O launcher traduz as opções nativas, usa o cache local e exige reinício após mudanças de código/configuração.','',
 '## Correções realizadas','',
 '- Provider Spark reutiliza a interface pública do cliente SDK e preserva modelo, parâmetros, consumo, término e contagem de tentativas. JSON segue no prompt, validado localmente com até um reparo; response_format não é enviado e não existe fallback automático entre modos.',
 '- Um turno é registrado antes da execução, captura conversa/perfil/histórico e bloqueia outra pergunta concorrente na mesma conversa. Rerun não é submissão. Falhas, perguntas incompletas e resultados desconhecidos ficam fora do próximo histórico semântico.',
 '- O armazenamento aplica operações sobre o estado atual, com revisão, lock entre processos e troca atômica. Não grava snapshots ao renderizar. Falha de gravação mostra aviso e permite salvar novamente sem executar o RAG. A migração cria backup; corrupção bloqueia a operação.',
 '- Fontes usam identidade estável por turno, deduplicação e validação de referências e destaques. Erros de metadados ficam localizados. Expansão e fontes sobrevivem à recarga. Excertos compactos seguem o limite configurado.',
 '- Erros aparecem junto à pergunta de origem. Perfil antigo não é trocado silenciosamente. Respostas parciais, abstenção e esclarecimento são estados concluídos distintos. Progresso do RAG usa o contexto da sessão somente durante o callback.',
 '- Foi corrigido o vínculo inicial de requisitos: rótulos inexistentes do planejador são vinculados aos requisitos canônicos do controlador. Vínculos já válidos são preservados; buscas posteriores continuam com rejeição estrita de IDs desconhecidos.',
 '- A saída detalhada do console CrewAI foi silenciada na aplicação. A sanitização de erros foi limitada ao agente da aplicação, preservando as causas usadas pelo feedback experimental.','',
 '## Testes','',f"**{tests['passed']} testes passaram**, sem falhas. Três integrações históricas ficaram fora desta execução porque exigem os snapshots congelados anteriores. Um teste adicional confirma que a referência antiga rejeita o novo orçamento da aplicação. Nenhuma verificação de assinatura foi relaxada.",'',
 'A bateria cobre duas sessões e processos, submissão/rerun, concorrência, migração, corrupção, gravação falhando e repetição apenas da gravação, resultado desconhecido, perfil congelado, token guard, parâmetros do SDK, fontes inválidas/repetidas e persistência dos destaques. O arquivo tests.xml registra os resultados.','',
 'Comando executado:','', '```sh',
 '.venv/bin/python -m pytest tests -q --tb=short \\\n  --deselect=tests/test_global_order_replay.py::test_real_offline_replay_is_reproducible_and_resumes_only_same_signature \\\n  --deselect=tests/test_document_budget_replay.py::test_real_experiment_is_offline_reproducible_and_keeps_current_window \\\n  --deselect=tests/test_document_budget_cycle.py::test_real_preflight_has_no_transport_and_checks_both_budgets',
 '```','', '## Chamadas reais pela página','',
 'As submissões foram sequenciais, em histórico separado do habitual e com o corpus existente. A tabela final abaixo distingue conclusão operacional de qualidade documental.','',
 '| Pergunta | Estado final | Chamadas lógicas | Tentativas HTTP de completion | Fontes citadas |','|---|---|---:|---:|---:|']
for row in final:lines.append('| '+str(row['question'])+' | '+row['state']+' | '+str(row['logical_calls'])+' | '+str(row['transport_attempts'])+' | '+str(row['sources'])+' |')
lines+=['','A pergunta documental terminou em abstenção no protocolo final. Isso é um resultado insuficiente para aquele caso conhecido, mesmo que o chat tenha concluído e salvo corretamente. As respostas com fontes de versões anteriores e o caso de continuação não autorizam afirmar melhora geral. Não foi aplicada regra especial para essas perguntas.','',
 '### Diagnósticos anteriores preservados','',
 'A primeira submissão com 8.192/3.000 foi bloqueada localmente: 9.392 tokens contados conservadoramente, mais saída e margem. A mudança para 16.384/6.000 foi autorizada pelo usuário.','',
 'O bloqueio refere-se àquela chamada específica; chamadas anteriores do mesmo turno podem ter ocorrido. A interface atual usa a expressão Esta chamada ao modelo não foi enviada para deixar isso claro.','',
 'Na etapa com esquema enviado também ao servidor, surgiram IDs iniciais inválidos, bloqueios conservadores de tamanho e um HTTP 500 no caso adicional sem suporte. Duas perguntas foram respondidas com fontes nessa etapa. O protocolo final usa JSON no prompt e validação local; não contamos o esquema duas vezes. A causa interna do HTTP 500 não foi confirmada com acesso ao servidor.','',
 'Cada tentativa, inclusive falhas, está em validation.json, com configuração, fingerprint do código, parâmetros, término, consumo e tempos. As versões de desenvolvimento não formam uma comparação controlada de qualidade. Os três casos finais podem ter fingerprints diferentes por causa de uma correção posterior restrita à sanitização de exceções; seus perfis individuais são preservados.','',
 '## Preservação e limitações','',
 'Os arquivos históricos protegidos foram conferidos por hash. A seção benchmark do TOML permaneceu idêntica à arquivada. O histórico habitual migrou para formato 2 com backup; suas mensagens foram preservadas. A validação real usou arquivos temporários separados. Um novo cache de índice foi produzido durante a preparação; o corpus não foi editado.','',
 'A montagem do prompt do RAG ainda precisa de investigação própria. O orçamento documental não limita sozinho instruções, contrato, fatos e operandos numéricos enviados ao modelo. Não houve promoção do controlador experimental, novo benchmark ou reativação de monitor.','',
 '## Rodar e reproduzir','',
 '```sh','.venv/bin/python run_streamlit.py','```','',
 f"Guia: [chat_spark.md]({ROOT/'docs/chat_spark.md'}). Testes visuais sintéticos: `.venv/bin/python -m streamlit run docs/analises/chat_spark_fixture.py --server.port=8519`.",'',
 'Detalhes: validation.json, validation_signature.json, preservation.json, tests.xml, screenshots/ e manifesto de hashes. As capturas distinguem dados sintéticos e execução real.']
(OUT/'relatorio.md').write_text('\n'.join(lines)+'\n')
style=(ROOT/'docs/analises/streamlit_audit_report.css').read_text()
style+='''nav{display:flex;flex-wrap:wrap;gap:1rem}.flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.flow>div{padding:1rem;border:1px solid var(--border)}.status{font-weight:600;color:var(--accent)}.case{border-bottom:1px solid var(--border);padding:1rem 0}.bar{height:1rem;background:var(--border);margin:.5rem 0 1.5rem}.bar span{display:block;height:100%;background:var(--accent)}details{margin-top:1rem}img{max-width:100%;height:auto}.notes{color:var(--text-dim)}@media(max-width:650px){.flow{grid-template-columns:minmax(0,1fr)}}'''
body='''<main><header><h1>O chat conecta. A qualidade ainda precisa de teste.</h1><p class="intro">O Qwen3.6 responde pela Spark. Conversas e fontes têm proteção. Uma pergunta documental ainda terminou em abstenção.</p></header>
<figure><div class="scope"><div><h3>Conexão e integridade</h3><div class="step">Pergunta aceita → um turno registrado → uma execução do RAG.</div><div class="step">Resposta → fontes validadas → gravação confirmada.</div></div><div><h3>Limite desta entrega</h3><div class="step">Uma execução pode fazer várias chamadas ao Qwen.</div><div class="step">Concluir e salvar não significa acertar a pergunta.</div></div></div><figcaption>O Streamlit está preparado para testes controlados; a qualidade documental não foi homologada.</figcaption></figure>
<section><h2>Os dois orçamentos usam réguas diferentes.</h2><figure><p>Janela local do Qwen · 16.384 tokens</p><div class="bar"><span style="width:100%"></span></div><p>Contexto dos documentos · 6.000 tokens BGE</p><div class="bar"><span style="width:100%"></span></div><figcaption>Não compare o comprimento das barras: os tokenizadores são diferentes. Pergunta, instruções, saída e margem também precisam caber na janela do Qwen.</figcaption></figure></section>
<section><h2>As três submissões finais têm resultados distintos.</h2><figure>'''
for row in final:
 body+='<div class="case"><h3>'+html.escape(row['question'] or '')+'</h3><p class="status">'+html.escape(row['state'])+'</p><p>'+str(row['logical_calls'])+' chamadas internas · '+str(row['transport_attempts'])+' tentativas HTTP · '+str(row['sources'])+' fontes citadas</p>'+(('<p>'+html.escape(row['error'])+'</p>') if row['error'] else '')+'</div>'
body+='''<figcaption>São testes de integração, sem avaliação independente da verdade das respostas. A abstenção no caso documental é uma pendência de qualidade, não prova de ausência da informação.</figcaption></figure></section>
<section><h2>As correções evitam perda e repetição.</h2><figure><div class="flow"><div><strong>Antes de chamar</strong><p>Reserva o turno e congela conversa, histórico e perfil.</p></div><div><strong>Durante a execução</strong><p>Mostra progresso e separa retry HTTP de reparo de JSON.</p></div><div><strong>Ao concluir</strong><p>Salva na origem; falha de disco repete só a gravação.</p></div></div><figcaption>Outra aba não pode substituir o histórico por um snapshot antigo. Timeout não provoca uma nova execução automática.</figcaption></figure></section>'''
body+=f'''<section><h2>Os testes isolados passaram; o uso real trouxe limites.</h2><figure><p class="status">{tests['passed']} testes aprovados</p><div class="bar"><span style="width:100%"></span></div><p>Três integrações históricas exigem os snapshots antigos.</p><figcaption>Os diagnósticos de desenvolvimento incluem bloqueios de tamanho e HTTP 500. Eles foram preservados; não foram escondidos nem convertidos em sucesso.</figcaption></figure><details><summary>Ver capturas da página e dos testes sintéticos</summary>'''
for filename,label in [('20-final-response.png','Página real: resposta e fontes'),('21-final-mobile.png','Página real em celular emulado'),('07-production-source-preview.png','Abertura de documento durante o desenvolvimento'),('14-fixture-error.png','Erro simulado na página completa'),('15-fixture-restored.png','Histórico sintético restaurado')]:
 p=OUT/'screenshots'/filename
 if p.exists():body+='<p>'+label+'</p><img loading="lazy" src="'+p.as_uri()+'" alt="'+label+'">'
body+='</details></section><section><h2>Como abrir o chat</h2><figure><pre><code>.venv/bin/python run_streamlit.py</code></pre><p>Reinicie depois de mudar o código ou a configuração. Chave e VPN continuam necessárias.</p><figcaption>O controlador experimental permanece separado. Esta etapa integra e protege o RAG V2 existente.</figcaption></figure><p>'
body+=' · '.join('<a href="'+(OUT/p).as_uri()+'">'+label+'</a>' for p,label in [('relatorio.md','Relatório completo'),('validation.json','Todas as tentativas'),('tests.xml','Testes'),('preservation.json','Preservação')])
body+='</p></section></main>'
page='<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chat Spark: correções e validação</title><style>'+style+'</style></head><body>'+body+'</body></html>'
for p in [ROOT/'docs/resultado_chat_spark_2026-10-19.html',Path.home()/'.agent/diagrams/chat_spark_corrigido_2026-10-19.html']:
 p.write_text(page)
print(json.dumps({'tests':tests,'final_cases':len(final),'costs':result['costs']},ensure_ascii=False))
