import json,sys,re,shutil
from pathlib import Path
ROOT=Path('/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC');sys.path.insert(0,str(ROOT))
from benchmark.core.reproducibility import sha
from benchmark.core import artifacts
OUT=ROOT/'docs/analises/14_incompletas_2026-10-16';a=artifacts.read_json(OUT/'audit.json');sp=artifacts.read_json(OUT/'supplement.json');source=Path(a['source'])
notes={
'E02':('Fontes alternativas','O agente encerrou na busca inicial. A ata de novembro/2025 associa o projeto RACK II à coordenação de Paulo Rego; a métrica exige o campo do plano RACK.','Revisar equivalência da fonte alternativa antes de chamar isso de falha semântica. Não mudar a nota congelada.'),
'C01':('Consulta e fontes alternativas','As buscas por coordenadores foram abertas, sem filtro de documento. Os dois campos anotados não vieram; atas no contexto ligam AFO a Fernando Trinta e RACK a Paulo Rego.','Buscas históricas com o mesmo texto e filtro do projeto recuperaram os campos. Há também suporte alternativo nas atas a auditar.'),
'C02':('Seleção comprovada','Todos os objetivos foram recuperados. O de RACK ficou fora do contexto principal, embora aparecesse em amostra adicional mostrada ao agente.','A combinação anotada requer 285 tokens. O agente não escolhe diretamente os blocos finais; não atribuir a perda somente à consulta ou somente ao reranker.'),
'C07':('Encerramento contraditório','Após apenas a busca inicial, a justificativa afirma que falta a ata de 13/07/2022, mas a ação é finish_sufficient.','Erro de decisão observável independentemente da nota: a justificativa contradiz a ação. A ata e o trecho existem no índice.'),
'C09':('Interpretação da pergunta','Encerrou após a busca inicial, tratando “Extraordinária” como modalidade. A comparação anotada é videoconferência versus reunião híbrida.','Não foram recuperadas as duas aberturas anotadas. Há pendência de alinhamento para JULY22_CHAIR; não tratá-la como ausência física comprovada.'),
'H01':('Investigação interrompida','Reconheceu que faltava o nome do coordenador e encerrou incompleta sem fazer busca complementar.','Ainda havia três buscas disponíveis. O campo de AFO existe no índice e já foi recuperado por outras consultas salvas; isso não é uma execução contrafactual do agente.'),
'H02':('Ligação entre projeto e pessoa','Fez duas buscas abertas, cada vez mais longas, ainda misturando o elo Redfish com o nome do coordenador. Encerrou suficiente sem o campo anotado.','A justificativa cita uma amostra para a coordenação; amostras não fazem parte do contexto final. Auditar a ligação e o período das outras atas antes de concluir suficiência semântica.'),
'H03':('Encerramento contraditório','A justificativa diz explicitamente que falta o nome do coordenador de SAAR; mesmo assim a ação é finish_sufficient, sem busca adicional.','O nome está num bloco curto no índice. Outras consultas salvas o recuperam. A contradição entre justificativa e ação é comprovada.'),
'H04':('Fontes alternativas','Encerrou na busca inicial. O contexto contém a declaração sobre o PET e outra ata que liga AFO a Fernando Trinta, mas não o campo AFO_NAME do plano.','Auditar a equivalência dessa ligação entre documentos; ausência da passagem anotada não prova ausência de toda evidência válida.'),
'H05':('Consulta mistura duas etapas','Uma decisão inválida foi corrigida, consumindo uma das quatro decisões. Depois buscou progressão e coordenação juntas, inclusive dentro do plano RACK.','O trecho da progressão foi encontrado; o elo coordenador↔RACK não foi comprovado pela âncora. Não separar a identificação da pessoa da busca de sua progressão pode prejudicar a recuperação.'),
'S01':('Cobertura de vários itens','Encerrou suficiente na busca inicial, faltando DevOps e o dashboard completos segundo as anotações.','O índice contém ambos; o dashboard está dividido entre dois blocos. O caso mistura recuperação de itens distribuídos e julgamento de suficiência do resumo.'),
'S04':('Continuação de trecho não recuperada','Recuperou discussão e votos, mas não o parágrafo final anotado com a decisão. Encerrou suficiente na busca inicial.','O parágrafo de encerramento está em outro bloco de 155 tokens do mesmo documento. Discussão e votação podem sustentar parte da conclusão; equivalência semântica exige revisão.'),
'Q02':('Fontes alternativas e fragmentação','O agente buscou mais uma vez no SAAR e encerrou suficiente. A ata de novembro/2025 traz os períodos de AFO II e SAAR II, mas a métrica exige rótulos e datas dos planos.','Nos planos, início, rótulos e término ficaram em quatro blocos por projeto, de 8–11 tokens. A falha da âncora não prova erro nas datas alternativas.'),
'Q10':('Consulta e fontes alternativas','Fez busca aberta e depois filtrada no RACK; o campo anotado não veio. O contexto possui atas que associam RACK a Paulo Rego.','A busca usou o nome longo do projeto, enquanto consultas históricas mais focadas no coordenador recuperaram o campo. Revisar também a evidência alternativa e sua edição/período.')}
rows=[]
for r in a['rows']:
 case=r['key'].split(':')[0].replace('REAL-','');group,finding,limit=notes[case]
 rows.append({'case':case,'group':group,'finding':finding,'limit':limit,
   'searches':len(r['search_states']),'stop':r['stop_reason'],'missing':r['missing_anchors'],
   'initial_only':len(r['search_states'])==1,'index_complete':all(r['full_index_hits'].values())})
# Verify no local reranking removed a candidate from any saved search of these cases.
original=artifacts.read_json(source/'D6000/retrieval.json')['results'];checked=0
for row in original:
 if row['key'] not in {r['key'] for r in a['rows']}:continue
 for search in row['diagnostics']['searches']:
  stages=search['diagnostics']['stages'];assert {x['chunk_id'] for x in stages['rrf']}=={x['chunk_id'] for x in stages['reranker']}
  checked+=1
manual={'name':'Por que faltou evidência?','audit_sha256':sha(OUT/'audit.json'),'supplement_sha256':sha(OUT/'supplement.json'),
 'analysis_script_sha256':sha(ROOT/'docs/analises/analisar_14_incompletas.py'),
 'facts':{'cases':14,'all_required_anchors_present_in_index':14,'incomplete_accumulated_candidate_pool':13,
  'selection_loss':1,'finish_sufficient_under_incomplete_frozen_metric':11,'initial_search_only':8,
  'explicit_reason_action_contradictions':['C07','H03'],'unchanged_local_candidate_sets_checked':checked},
 'semantic_review_candidates':['E02','C01','H04','Q02','Q10'],
 'semantic_review_status':'Manual source observations only; no semantic score, new rates or revised benchmark labels.',
 'rows':rows,'new_model_calls':0,'new_searches':0,'new_rerankings':0}
artifacts.save_json(OUT/'findings.json',manual)
lines=['# Por que faltou evidência? Análise das 14 perguntas','',
'**Há problemas em mais de uma etapa. Os 14 casos são incompletos pela métrica congelada; não são 14 falhas semânticas comprovadas.** Esta análise usa somente o índice e os registros existentes, sem modelo, buscas ou rerankings novos.','',
'## O que foi comprovado','',
'- Todas as passagens anotadas faltantes existem nas representações de blocos do índice. Não se constatou perda total desses trechos na ingestão. Isso não significa que sejam fáceis de recuperar.',
'- Em 13 casos, as consultas executadas não acumularam todas as passagens anotadas. A ausência já aparece no conjunto anterior ao reranking local. Os 27 conjuntos locais conferidos conservaram os mesmos candidatos após esse reranking.',
'- Em C02, os três objetivos foram encontrados, mas o de RACK ficou fora da seleção principal. O agente o recebeu em uma amostra extra. A combinação necessária tem 285 tokens e cabia no limite.',
'- Oito casos pararam após a busca inicial. Onze escolheram finish_sufficient sem todas as passagens anotadas no contexto. São contagens sobrepostas, não uma divisão de culpa.',
'- Em C07 e H03 há uma contradição direta: a justificativa reconhece a informação faltante e a ação declara suficiência.',
'- Há fontes alternativas relevantes em E02, C01, H04, Q02 e Q10. Não recalculamos completude com outro critério. S04 e H02 também precisam de cautela semântica sobre inferência da decisão e ligação entre pessoa, projeto e período.','',
'## Um problema geral de representação','',
'Os blocos de coordenação têm 10–12 tokens e contêm apenas o rótulo e o nome, sem o nome do projeto no próprio texto. Datas e seus rótulos ficaram separados em quatro blocos de 8–11 tokens por projeto. O dashboard SAAR está dividido em dois blocos. Essa fragmentação é observável; seu efeito causal precisa de comparação própria.','',
'Existem consultas históricas já executadas que recuperaram cada uma das 11 âncoras distintas faltantes. Em C01 há consultas com o mesmo texto e filtro no documento correto que recuperaram os coordenadores. Isso prova recuperabilidade para essas entradas salvas, não que o agente escolheria esses filtros nem que uma regra de filtro resolveria todos os casos.','',
'## Os 14 casos','',
'| Caso | Buscas com a original | Encerramento | Diagnóstico |','|---|---:|---|---|']
for r in rows:lines.append(f"| {r['case']} | {r['searches']} | {r['stop']} | {r['group']} |")
for r in rows:
 x=next(x for x in a['rows'] if x['key'].startswith('REAL-'+r['case']+':'))
 lines+=['','### '+r['case'],'',x['question'],'',r['finding'],'',r['limit'],'',
 'Passagens anotadas faltantes: '+', '.join(r['missing'])+'.', '',
 'Consultas executadas:']
 for q in x['search_states']:lines.append('- '+q['query_id']+': '+q['query']+(' [filtro documental]' if q['scope'] else ' [coleção inteira]'))
lines+=['','## Como interpretar a responsabilidade','',
'Para os 13 casos, comprovamos uma falha de cobertura da recuperação **com aquelas consultas e filtros**. Ainda não isolamos quanto veio da consulta, da representação dos trechos ou do ranking dos canais denso/esparso. O reranker local não excluiu candidatos nesses casos; não poderia recuperar um bloco que nunca entrou na união. Isso não é uma ablação nem prova que o reranker seja dispensável.','',
'O agente contribuiu com paradas sem buscas complementares, consultas que misturam etapas e duas ações contraditórias à própria justificativa. Em parte dos casos, contudo, ele encontrou fontes alternativas plausíveis que a métrica não reconhece. Portanto, o número 11 não pode ser lido automaticamente como 11 decisões semanticamente erradas.','',
'## Próxima investigação recomendada','',
'Primeiro auditar a aceitação de evidências equivalentes com uma regra geral, mantendo evidence_v2 e literal_v1 históricos intactos. Se uma nova avaliação for criada, ela deve ser versionada e aplicada às 70 perguntas e aos dois braços, sem corrigir somente as reprovadas.','',
'Depois separar testes de representação dos blocos e de decisão do agente, um fator por comparação. Os dados atuais justificam estudar blocos que preservem relações rótulo–valor e projeto–pessoa, além de encerramentos coerentes. Não justificam simplesmente desligar o reranker ou criar regras específicas para perguntas.','',
'Arquivos: audit.json (índice, buscas e observações), supplement.json (consultas históricas já executadas), findings.json (interpretação explícita) e preservation.json. As notas e os históricos da rodada original permanecem inalterados.']
# Replace computed count rather than hardcoding it.
lines=[s.replace('Os 27 conjuntos locais',f'Os {checked} conjuntos locais') for s in lines]
(OUT/'relatorio.md').write_text('\n'.join(lines)+'\n')
old=Path('/Users/fernandotrinta/.agent/diagrams/teste_completo_dobro_documentos_2026-10-16.html').read_text();head=old.split('<style>')[0].replace('Teste completo com o dobro de documentos','Por que faltou evidência?');style=re.search(r'<style>(.*?)</style>',old,re.S).group(1)
extra='''details{border-top:1px solid var(--border);padding:1rem 0}summary{cursor:pointer;font-weight:600}details p{max-width:68ch;margin-top:1rem}.flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.flow div{padding:1rem;border:1px solid var(--border)}.flow strong{display:block;font-size:2.25rem}.allcases{display:grid;grid-template-columns:minmax(0,1fr)}.case-meta{color:var(--text-dim);font-size:.875rem}.warning{border:1px solid var(--border-bright);padding:1rem;margin-top:1rem}.case-query{font-size:.875rem;color:var(--text-dim);margin:1rem 0;overflow-wrap:anywhere}@media(max-width:650px){.flow{grid-template-columns:minmax(0,1fr)}}'''
body='''<main><header><p class="muted">ANÁLISE DOS CASOS · 16 OUT 2026</p><h1>A falha não tem um único dono.</h1><p class="intro">Os 14 casos misturam recuperação, escolhas do agente e seleção. E algumas informações aparecem em fontes alternativas que a métrica não aceita.</p></header><figure><div class="flow"><div><strong>14 / 14</strong>As passagens esperadas existem no índice.</div><div><strong>13 / 14</strong>As buscas executadas não trouxeram todas as passagens anotadas.</div><div><strong>1 / 14</strong>C02: encontrou tudo, mas deixou parte fora do contexto principal.</div></div><figcaption>Isso localiza a ausência medida. Não distribui a culpa entre agente e retriever; as causas podem coexistir.</figcaption></figure>
<section><h2>A métrica não reconhece toda fonte equivalente.</h2><figure><div class="scope"><div><h3>E02 · coordenação do RACK II</h3><div class="step">O contexto contém uma ata que liga o projeto ao coordenador.</div><div class="step">O avaliador exige o campo “Coordenador na Instituição” do plano RACK.</div></div><div><h3>Q02 · datas de AFO II e SAAR II</h3><div class="step">A ata de novembro/2025 informa os períodos dos dois projetos.</div><div class="step">O avaliador exige os rótulos e valores dos planos de trabalho.</div></div></div><figcaption>Os dois continuam reprovados pela métrica congelada. Isso não demonstra ausência de informação válida. C01, H04 e Q10 também têm fontes alternativas relevantes para auditoria.</figcaption></figure><p class="intro">Não mudamos nenhuma nota. Uma nova regra de equivalência precisaria ser geral, versionada e aplicada às 70 perguntas dos dois braços.</p></section>
<section><h2>O agente também deixou de investigar.</h2><figure><div class="scope"><div><h3>Oito pararam na primeira busca</h3><p class="transition">E02 · C07 · C09 · H01 · H03 · H04 · S01 · S04</p><p class="muted">Ainda havia três buscas disponíveis. Isso pede revisão; não prova sozinho que toda parada foi errada.</p></div><div><h3>Duas decisões se contradizem</h3><div class="step">C07 e H03: a justificativa diz que falta informação.</div><div class="step"><strong>Ação escolhida: “evidência suficiente”.</strong></div></div></div><figcaption>As duas contradições são observáveis sem trocar o avaliador. Onze declarações de suficiência falham na métrica original, mas parte delas pode usar fontes equivalentes.</figcaption></figure></section>
<section><h2>Há trechos pequenos sem o contexto necessário.</h2><figure><div class="scope"><div><h3>Nome de coordenador · 10–12 tokens</h3><div class="step">Coordenador na Instituição<br><strong>Nome da pessoa</strong></div><p class="muted">O projeto está nos metadados, mas não aparece nesse texto. A consulta compete com vários blocos parecidos.</p></div><div><h3>Datas · quatro blocos por projeto</h3><div class="step">Data de início: │ 01/03/2026<br>Data de término: │ 28/02/2027</div><p class="muted">Cada rótulo e cada valor ficaram separados. O dashboard SAAR também ocupa dois blocos.</p></div></div><figcaption>É um problema de representação observável. Consultas históricas salvas conseguiram recuperar os campos; isso não demonstra que o agente atual faria as mesmas consultas.</figcaption></figure></section>
<section><h2>Inspecione cada pergunta.</h2><figure><div class="allcases">'''
import html
for r in rows:
 x=next(x for x in a['rows'] if x['key'].startswith('REAL-'+r['case']+':'))
 body+=f'<details><summary>{r["case"]} · {html.escape(r["group"])}</summary><p><strong>{html.escape(x["question"])}</strong></p><p>{html.escape(r["finding"])}</p><p class="muted">{html.escape(r["limit"])}</p><p class="case-meta">{r["searches"]} busca(s), incluindo a original · ação final: {r["stop"]} · faltam na métrica: {", ".join(r["missing"])}</p>'
 for q in x['search_states']:body+=f'<div class="case-query">{q["query_id"]} · {html.escape(q["query"])} · {"com filtro documental" if q["scope"] else "coleção inteira"}</div>'
 body+='</details>'
body+='''</div><figcaption>A classificação é uma interpretação dos registros, sem novas buscas ou decisões. As notas do benchmark permanecem intactas.</figcaption></figure></section><section><h2>O próximo passo começa pela medição.</h2><p class="intro">Auditar fontes equivalentes antes de tratar os 14 casos como falhas semânticas. Depois testar, separadamente, a representação dos trechos e as decisões de continuar ou encerrar.</p><p class="intro muted">Não há evidência aqui para simplesmente remover o reranker. Nos conjuntos conferidos, ele preservou todos os candidatos que recebeu.</p></section><section class="sources"><h2>Registros verificáveis</h2><p>'''
body+=' · '.join(f'<a href="{(OUT/f).as_uri()}">{label}</a>' for f,label in [('relatorio.md','Relatório completo'),('audit.json','Índice e observações'),('supplement.json','Buscas históricas'),('findings.json','Interpretação'),('preservation.json','Preservação')])
body+='</p><p class="muted">Zero novas chamadas ao modelo, zero buscas e zero rerankings. As anotações foram usadas somente na análise posterior à seleção.</p></section></main>'
page=head+'<style>'+style+extra+'</style></head><body>'+body+'</body></html>'
for p in [Path('/Users/fernandotrinta/.agent/diagrams/analise_14_incompletas_2026-10-16.html'),ROOT/'docs/resultado_analise_14_incompletas_2026-10-16.html']:
 assert not p.exists();p.write_text(page)
shutil.copyfile('/tmp/report_14_cases.py',OUT/'report_script.py')
print({'cases':len(rows),'local_candidate_sets_verified':checked,'initial_only':sum(r['initial_only'] for r in rows)})
