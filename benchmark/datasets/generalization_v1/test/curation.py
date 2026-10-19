import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from benchmark.evidence_v2 import normalized,source_end
from benchmark.generalization_dataset import compile_dataset
root=Path('benchmark/datasets/generalization_v1');inventory=json.loads((root/'inventory.json').read_text());assert (root/'development_freeze.json').exists()
by={f['family_id']:f['documents'][0] for f in inventory['families']}
def proof(f,start,end):
 p=Path('data/collections')/by[f]['relative_path'];raw=p.read_text();s,m=normalized(raw);a=s.index(start);b=s.index(end,a)+len(end)
 return {'document':p.name,'quote':raw[m[a]:source_end(raw,m[b-1])]}
def row(cat,q,a,field,e,bridge=''):return {'category':cat,'question':q,'expected_answer':a,'field':field,'evidence':e,'bridge':bridge}
M='multi-hop';C='single-document factual';X='cross-document';multi=[];controls=[];cross=[]
def add(f,q,a,field,s1,e1,s2,e2,bridge,cq,ca,cf,cs,ce):
 multi.append(row(M,q,a,field,[proof(f,s1,e1),proof(f,s2,e2)],bridge));controls.append(row(C,cq,ca,cf,[proof(f,cs,ce)]))
add('GF15','Na ata de abril de 2021, qual projeto recebeu parecer favorável do suplente da banca de progressão de João Paulo Pordeus?','Proactive Monintoring Based On Machine Learning.','project_review',
 'o chefe do departamento solicitou a aprovação da banca','Prof. José Maria como suplente.',"aprovação do Projeto 'Proactive","à bolsa referente a coordenação para o professor Miguel Franlin.",'A banca identifica José Maria; seu parecer identifica o projeto em outro item.',
 'Na ata de abril de 2021, qual bolsa mensal foi prevista para Joseane Oliveira Vale Paiva no FRDI-Phase II?','R$ 2.250,00.','scholarship_value','5. Joseane Oliveira Vale Paiva','todas elas com duração de 10 meses.')
add('GF16','Em abril de 2022, que carências do CIPEMAC foram apontadas pelo professor que substituiu João Paulo Pordeus na bolsa do convênio com a SEFAZ-MA?','Sem bebedouro, salas sem móveis e equipamentos.','infrastructure_needs',
 'aprovou por ad referendum a substituição','por 18 meses.','o Prof. Ângelo solicitou melhorias','salas sem móveis e equipamentos.','A substituição identifica Ângelo, que relata as carências em outro ponto.',
 'Quanto e por quantos meses receberia Pedro Almir no DELL Scope Management Tool PHASE II segundo abril de 2022?','R$ 2.000,00 por 11 meses.','scholarship_value','O Prof. Miguel Franklin relatou a bolsa de pesquisa','(a partir de abril/ 2022).')
add('GF17','Na ata de abril de 2023, para quais classes foi aprovada a progressão que recebeu parecer do presidente da comissão de avaliação de Ana Karolinna?','Pablo Mayckon: Professor Adjunto C II para Professor Adjunto C III.','career_progression',
 'formação da Comissão de Avaliação Docente','supracitada comissão a qual foi aprovada pelo Colegiado.','o Prof. Rudini Menezes apresentou Parecer','Professor Adjunto C III.','A comissão identifica Rudini; outro parecer dele identifica a progressão de Pablo.',
 'Qual orçamento total foi informado em abril de 2023 para o Lenovo Diagnostics Evolution Chatbot?','R$ 10.840.158,56.','project_budget','o Prof. Lincoln Rocha relatou o Projeto de Pesquisa intitulado','(01/07/2023 a 31/12/2024).')
add('GF18','Quais projetos Lenovo tiveram anexos sobre dados pessoais relatados, em abril de 2025, pelo docente que viajaria ao IEEE Symposium on Security and Privacy?','CH-IA e LDAR.','data_protection_amendments',
 '4ª Matéria: Afastamento internacional','durante o afastamento.','5ª Matéria: Aprovação de Termo Aditivo','também precisará que se elabore um Anexo de Tratamento de Dados Pessoais, não envolvendo aumento de prazo e nem de recursos.','O afastamento identifica Javam; os dois aditivos relatados por ele identificam CH-IA e LDAR.',
 'Qual orçamento estimado do Wise Control foi aprovado em abril de 2025?','R$ 775.554,00.','project_budget','7ª Matéria: Aprovação do Projeto','quinhentos e cinquenta e quatro reais).')
add('GF19','Na reunião extraordinária de maio de 2020, para qual comissão foi indicado o professor que relatou a prorrogação do projeto de manutenção preditiva com a Delfos?','Comissão Eleitoral para eleição da chefia, biênio 2020-2022.','committee_membership',
 'o Prof. João Paulo Pordeus relatou a extensão','não havia adicional de recurso financeiro.','indicação de Comissão Eleitoral','composição da referida Comissão,','O relato da Delfos identifica Pordeus, depois indicado para a comissão eleitoral.',
 'Em maio de 2020, qual duração e início da licença para interesses particulares solicitada por Rosely Araújo?','Três anos a partir de 01/07/2020.','leave_period','solicitação de licença para trato de interesses particulares','servidora técnico-administrativa Rosely Araújo.')
add('GF20','Em maio de 2021, qual espaço foi cedido temporariamente aos projetos de segurança pública depois de ser desocupado pelo professor cuja participação no PROPAP foi aprovada?','Laboratório BIMO, Bloco 952.','laboratory_allocation',
 'a solicitação do Professor Aposentado Fernando Carvalho','laboratório BIMO que funcionava no Bloco 952, anexo ao DC.','a solicitação dos Professores Emanuele Santos e Fernando Trinta','durante a execução dos projetos em pauta.','O pedido de PROPAP identifica o espaço antes ocupado; outro item documenta sua cessão.',
 'Qual período da renovação do afastamento parcial de Daniel Ribeiro Matos foi aprovado em maio de 2021?','10/05/2021 a 02/09/2021.','leave_period','pedido de renovação do afastamento parcial','junto ao Programa de Pós-Graduação em Ciência da Computação da UFC.')
add('GF21','Na reunião de maio de 2022, além de Valéria Lelli, qual outro docente tinha uma comissão de progressão presidida pela professora que substituiu Paulo Rego na avaliação de Valéria?','João Bosco Ferreira.','career_committee',
 'nova Comissão de Avaliação do processo de Progressão','José Maria da Silva Monteiro Filho e Lincoln Souza Rocha.','o Prof. João Bosco Ferreira solicitou alteração','Fernando Antonio Mota Trinta e Lincoln Souza Rocha.','A primeira comissão identifica Rossana; a outra liga Rossana à avaliação de João Bosco.',
 'Quais disciplinas e cargas horárias foram aprovadas para Engenharia Metalúrgica em maio de 2022?','Cálculo Numérico e Programação Computacional para Engenharia, ambas 64h e obrigatórias.','teaching_offer','o Coordenador do Curso de Engenharia Metalúrgica','(Processo SEI 23067.023636/2022-74).')
add('GF22','Na ata de maio de 2023, qual orçamento do projeto sobre governança da educação básica foi relatado pelo docente que receberia uma bolsa de R$ 3.000,00 no CEREIA?','R$ 10.639.266,00.','project_budget',
 'o Prof. João Paulo Pordeus relatou a bolsa de pesquisa do Prof. César Lincoln','por sessenta meses (5 anos).','o Prof. César Lincoln relatou o projeto intitulado:','duzentos e sessenta e seis reais).','A bolsa CEREIA identifica César Lincoln; sua relatoria identifica o orçamento do FNDE.',
 'Qual antecedência mínima de comunicação à chefia foi adotada em maio de 2023 para afastamentos a partir de 15 dias?','Três dias antes da reunião em que o afastamento seria votado.','absence_procedure','Proposta: Este Departamento adotará como prática interna','pertencente à Unidade Curricular de suas disciplinas.')
add('GF23','Na ata de maio de 2024, qual orçamento do projeto Lenovo relatado pelo professor que propôs implementar posteriormente o piloto de plenário virtual?','R$ 1.705.533,00.','project_budget',
 'Proposta 2 (sugerida pelo Prof. Ângelo Brayner):','implementar a posteriori.','o Prof. Angelo Brayner relatou o projeto de pesquisa:','quinhentos e trinta e três reais).','A proposta identifica Ângelo; a relatoria dele identifica o orçamento LTAD.',
 'Em que dias ocorreria o II Workshop de Testes de Segurança do GREat aprovado em maio de 2024?','09 e 10/05/2024.','event_dates','a Profa. Valéria Lelli relatou','nos dias 09 e 10/05/2024.')
add('GF24','Na ata de maio de 2025, quem presidia a comissão de progressão do outro professor que pediu adiamento da reunião de junho junto com Yuri Lenon?','Javam de Castro Machado, na comissão de Ângelo Brayner.','career_committee',
 '12ª Matéria: Discussão sobre a possibilidade de adiamento','a pedido dos Professores Yuri Lenon e Ângelo Brayner.','11ª Matéria: Aprovação de Comissão de Avaliação','supracitada comissão, que foi aprovada por unanimidade pelo Colegiado.','O pedido conjunto identifica Ângelo; outro item identifica Javam como presidente de sua comissão.',
 'Para qual orçamento total passou o LTAD após o aditivo aprovado em maio de 2025?','R$ 5.853.275,80.','project_budget','13ª Matéria: Aprovação de Aditivo','setenta e cinco reais e oitenta centavos).')
add('GF25','Na ata de junho de 2020, qual representante dos servidores compunha a comissão eleitoral junto com a docente responsável pelo projeto de coleta de métricas de testes de software?','Felipe Peixoto Gomes.','electoral_representation',
 "o professor João Paulo Pordeus Gomes relatou sobre a aprovação do projeto, intitulado 'Pesquisa e desenvolvimento de tecnologia para automatização",'em parceria com a empresa Dell Computadores do Brasil LTDA,','a Comissão Eleitoral é formada','como representante dos alunos;','O projeto identifica Emanuele; a composição eleitoral com ela identifica Felipe.',
 'Qual orçamento do Interlocks Audit Tool foi apresentado em junho de 2020?','R$ 459.468,24.','project_budget',"2. O projeto intitulado 'Interlocks Audit Tool'",'vinte e quatro centavos).')
add('GF26','Segundo junho de 2021, que empresa manifestou interesse em projetos com o DC ao professor convidado para preparar o curso do Grupo O POVO?','Samsung.','company_interest',
 'um convite feito ao Prof. José Antônio Macedo','para o Grupo de Comunicação O POVO.','o Prof. José Antônio Macedo informou','pesquisadores do Departamento de Computação.','O convite identifica Macedo; outro relato dele identifica Samsung.',
 'Em junho de 2021, qual valor do prêmio ao qual Ana Karolinna concorreria com o projeto sobre caminhos em dígrafos?','R$ 50.000,00.','award_value','a Profa. Ana Karolinna Maia informou','para executar o projeto.')
add('GF27','Na ata de junho de 2022, para qual cidade iria ao ACM SIGMOD o docente cuja bolsa no GALP foi renovada por oito meses?','Filadélfia, USA.','travel_destination',
 'renovação de uma bolsa de pesquisa destinada ao Prof. Javam Machado','do Departamento de Física.','o Prof. Javam Machado relatou seu afastamento','no período de 13 a 26/06/2022.','A bolsa GALP identifica Javam; seu afastamento identifica Filadélfia.',
 'Qual prazo para concluir a atualização dos planos do novo PPC foi informado em junho de 2022?','17/06/2022.','teaching_plan_deadline','o Prof. Pablo, na qualidade de vice-coordenador do curso','o dia 17/06/2022.')
add('GF28','Na ata de junho de 2024, qual destino do afastamento para ICML do docente escolhido como novo suplente de Lógica, Inteligência Artificial e Probabilidade?','Viena, Áustria.','travel_destination',
 'o Colegiado aprovou os nomes dos Professores Javam Machado (suplente)','Lógica, Inteligência Artificial e Probabilidade, respectivamente.','o Prof. César Lincoln relatou seu pedido de afastamento','durante o período de 21/07/2024 a 28/07/2024.','A substituição curricular identifica César Lincoln; seu afastamento identifica Viena.',
 'Qual orçamento do ReArte foi apresentado na reunião de junho de 2024?','R$ 2.004.390,00.','project_budget','o Prof. José Maria Monteiro relatou o Projeto de Pesquisa intitulado','(12 meses).')
add('GF29','Na ata de junho de 2025, até quando duraria o mandato no Conselho do Centro do professor que apresentou o parecer de progressão de Ana Karolinna?','Até setembro de 2026, para Heron Carvalho.','representation_term',
 '11ª Matéria: Aprovação de Parecer','Parecer favorável à Progressão Funcional da Profa. Ana Karolinna Maia.','o Prof. Heron Carvalho se predispôs','com mandato até setembro de 2026.','O parecer identifica Heron; sua indicação ao conselho informa o mandato.',
 'Na ata de junho de 2025, qual novo nome e orçamento substituíram o Sales CRM Performance Improvements?','Inventory and Logistics Modernization; R$ 2.422.401,09.','project_rename_budget','3ª Matéria: Homologação','quatrocentos e um reais e nove centavos).')
add('GF30','Na ata de julho de 2020, qual bolsa no projeto de Self-Healing foi aprovada para o docente cuja banca de progressão incluía João Paulo Pordeus e Yuri Lenon?','R$ 3.000,00 por seis meses, para César Lincoln.','scholarship_value',
 'Prof. João Fernando, na presidência, Prof. João Paulo Pordeus','para a banca do Prof. César Lincoln;',"O segundo projeto é intitulado 'Pesquisa e Desenvolvimento de Tecnologia de Self-Healing",'iniciando em julho de 2020.','A banca identifica César Lincoln; a bolsa de Self-Healing é vinculada a ele em outro ponto.',
 'Qual valor e duração da bolsa de Antônio Diogo Forte Martins no Lenovo Chatbot foram aprovados em julho de 2020?','R$ 1.600,00 por seis meses.','scholarship_value','uma bolsa de pesquisa para o aluno de mestrado Antônio Diogo','coordenado pelo Prof. Javam Machado.')
add('GF31','Na ata de julho de 2021, entre quais classes progrediu o professor escolhido para presidir a comissão inicial de colaboração com o DEMA no novo curso de Ciência de Dados?','Ângelo Brayner: Adjunto CI para Adjunto CII.','career_progression',
 'o Colegiado decidiu formar uma comissão inicial','na estruturação desse Projeto de Curso.','o Prof. Javam Machado apresentou Parecer','Professor Adjunto CI para Adjunto CII.','A comissão identifica Ângelo; o parecer anterior documenta sua progressão.',
 'Para qual valor total passou o eHealth-Risk após a alteração aprovada em julho de 2021?','R$ 794.283,85.','project_budget','uma alteração no montante e tempo de duração do Projeto de Pesquisa:','oitenta e cinco centavos).')
add('GF32','Na ata de julho de 2022, qual bolsa do AI4Wellness seria paga ao docente eleito chefe na chapa vencedora?','João Paulo do Vale: R$ 5.000,00 por 57 meses.','scholarship_value',
 'Chapa 1: Prof. João Paulo do Vale Madeiro (Chefe)','Prof. Fernando Antonio Mota Trinta (Subchefe).','2.uma bolsa de pesquisador sênior','por 57 meses.','A eleição identifica Madeiro; a bolsa sênior no outro item é destinada a ele.',
 'Qual valor e duração da bolsa de Lívia Iorrana Jucá Eugênio na residência UFC/Samsung/SiDi foram informados em julho de 2022?','R$ 2.500,00 por 14 meses.','scholarship_value','bolsa de inovação da aluna Lívia','por 14 meses.')
add('GF33','Na ata de julho de 2023, quantos semestres deveriam ser examinados no levantamento de carga horária proposto pelo docente cuja progressão de CII para CIII foi aprovada?','Quatro semestres seguidos.','workload_review',
 'o Prof. José Maria Monteiro apresentou Parecer favorável','Professor Adjunto CIII.','o Prof. Ângelo Brayner sugeriu a seguinte proposta:','possibilidade de oferta da referida disciplina.','A progressão identifica Ângelo; sua proposta exige levantamento por quatro semestres.',
 'Quantas vagas por semestre eram previstas para Introdução à Programação em Engenharia de Alimentos na reunião de julho de 2023?','50 vagas por semestre para cada turma.','teaching_capacity','essa disciplina é obrigatória para o Curso de Engenharia de Alimentos','a previsão de início para 2024/1.')
add('GF34','Na ata de julho de 2024, em que cidade ocorreria a missão científica do professor que se comprometeu a pintar a sala para substitutos e visitantes?','New York, USA.','travel_destination',
 'O Prof. Javam Machado se comprometeu em pintar','própria para uso.','o Prof. Javam Machado solicitou afastamento do país','durante o período de 01/09/2024 a 30/09/2024.','A pintura identifica Javam; sua missão ao AT&T informa New York.',
 'Qual bolsa do ABIN Connect para Francisco Victor da Silva Pinheiro foi aprovada em julho de 2024?','R$ 3.100,00 por 12 meses.','scholarship_value','o Prof. Paulo Rego relatou a aprovação da chefia, por ad referendum, à implementação de bolsa de doutorado','(julho/2024 a junho/2025).')
assert len(multi)==20 and len(controls)==20
financial=[]
def fin(f,question,answer,start,end):financial.append((f,question,answer,proof(f,start,end)))
fin('GF35','qual bolsa do Kunumi Lab para Javam aparece em julho de 2025','R$ 4.000,00 por 12 meses','4ª Matéria: Homologação de ad referendum : Participação do Prof. Javam Machado','por 12 meses.')
fin('GF36','para qual valor passou a bolsa de Emanuele no projeto de coleta de métricas em agosto de 2020','R$ 6.000,00','a Profa. Emanuele Marques informou sobre a alteração','para R$ 6.000,00 (seis mil reais).')
fin('GF37','qual bolsa Brazil ID para Paulo Rego aparece em agosto de 2021','R$ 3.060,00 por sete meses','uma bolsa de pesquisador Sênior para o Prof. Paulo Rego','(julho/2021 a janeiro/2022).')
fin('GF38','qual bolsa GTT para Fernando Trinta aparece em agosto de 2023','R$ 5.000,00','o Prof. Lincoln Rocha relatou a extensão da bolsa','no período de agosto/23 a fevereiro/2024.')
fin('GF39','qual renovação da bolsa de Joaquim Bento na Petrobras aparece em agosto de 2024','R$ 3.520,00 por sete meses','o Prof. João Paulo Madeiro relatou a renovação de bolsa','(três mil, quinhentos e vinte reais).')
fin('GF40','qual renovação da bolsa de José Maria no LTAD aparece em agosto de 2025','R$ 9.000,00 por 20 meses','8ª Matéria: Bolsa para o Prof. José Maria','por 20 meses a partir de agosto/2025.')
fin('GF41','qual bolsa de Emanuele no chatbot Dell aparece em setembro de 2021','R$ 4.000,00','o Prof. João Paulo Pordeus relatou o pedido de bolsa de pesquisa','sob coordenação do Prof. Lincoln Rocha.')
fin('GF42','qual bolsa de César Lincoln no AI4Wellness aparece em setembro de 2022','R$ 5.000,00 por 56 meses','as bolsas de pesquisa vinculadas ao Projeto de P&D intitulado:', 'por 56 meses;')
fin('GF43','qual placar da segunda votação sobre interesse na remoção de Camilo aparece em setembro de 2023','14 a favor, quatro contra e três abstenções','Na sequência, houve a 2a. votação','03 (três) abstenções.')
fin('GF44','quem compôs a comissão julgadora e a secretaria do Edital 78/2024 na ata ordinária de setembro de 2024','Pablo Mayckon, César Lincoln e Yuri Lenon; secretário Emanuel Rodrigues','8ª Matéria: Indicação de Comissão Julgadora','o professor Emanuel Rodrigues;')
fin('GF45','qual candidato venceu o Edital 78/2024 na ata extraordinária de setembro de 2024','André Luís da Costa Mendonça','o certame contou com apenas um candidato inscrito','conforme Edital Nº 78/2024.')
fin('GF46','quantas disciplinas Pablo ministrava e quantas ainda estavam sem professor na ata ordinária de setembro de 2025','Três ministradas por Pablo e duas sem professor','5ª Matéria: Alocação temporária','ainda havendo 2 disciplinas sem professor.')
fin('GF47','qual documento faltava às inscrições do Edital 106/2025 na ata extraordinária de setembro de 2025','Anuência do coordenador do curso e do orientador','apenas dois candidatos, ambos doutorandos do MDCC','no caso de candidato aluno de programa de pós-graduação stricto sensu,')
fin('GF48','qual novo valor da bolsa de Emanuele na coleta de métricas aparece em outubro de 2020','R$ 7.000,00','a Profa. Emanuele Santos informou que houve alteração','para R$ 7.000,00 (sete mil reais).')
fin('GF49','qual orçamento total do Connor aparece em outubro de 2021','R$ 2.655.956,25','o Prof. Joaquim Bento relatou o Projeto de fomento à inovação','durante o período de 01/12/2021 a 31/01/2024.')
fin('GF50','qual custo da extensão de dois meses do projeto Dell de cobertura por mapas aparece em outubro de 2022','R$ 264.231,27','o Prof. João Paulo Pordeus relatou o Termo Aditivo','vinte e sete centavos).')
fin('GF51','quais cargas horárias de Tecnologias Digitais e Sociedade e de Informática e Sociedade foram contrastadas na ata extraordinária de outubro de 2023','64h e 32h, respectivamente','O Chefe inicia a discussão apresentando','será necessário que a turma do curso de Ciências Biológicas tenha mais um dia de aula para completar a quantidade de créditos.')
fin('GF52','qual orçamento da engine de vídeo para eventos de trânsito aparece na ata ordinária de outubro de 2023','R$ 308.020,00','o Prof. Paulo Rego relatou o projeto de pesquisa intitulado','(trezentos e oito mil e vinte reais).')
fin('GF53','quais bolsas de César Lincoln e Emanuel no Copiloto de Gestão de Vulnerabilidades aparecem em outubro de 2025','R$ 6.000,00 e R$ 6.500,00, respectivamente','5ª Matéria: Homologação','R$ 6.500,00 (seis mil e quinhentos reais).')
fin('GF54','qual orçamento da parte LDAR após o desmembramento aparece em novembro de 2021','R$ 2.346.118,60','A primeira parte do Projeto intitulada:', 'durante o período de jan/2022 a dez/2022.')
# Two financial cycles and one staffing/teaching cycle: each fact appears twice.
staff_ids={'GF43','GF44','GF45','GF46','GF47','GF51'}
money=[x for x in financial if x[0] not in staff_ids];staff=[x for x in financial if x[0] in staff_ids]
assert len(money)==14 and len(staff)==6
for group,field in [(money[:7],'cross_document_financial_comparison'),(money[7:],'cross_document_financial_comparison'),(staff,'cross_document_staffing_teaching')]:
 for idx,a in enumerate(group):
  b=group[(idx+1)%len(group)]
  prefix=['Consultando as duas atas,','Comparando os registros,','Para reunir as informações dos dois períodos,','Quais informações constam nas duas atas:'][idx%4]
  cross.append(row(X,prefix+' '+a[1]+' e '+b[1]+'?',a[2]+'; '+b[2]+'.',field,[a[3],b[3]]))
rows=multi+controls+cross
compile_dataset(rows,inventory,'test',root/'test')
freeze=json.loads((root/'development_freeze.json').read_text())
(root/'test/source_audit.json').write_text(json.dumps({'status':'reviewed_against_markdown','method':'Implementing agent manually curated all questions, answers, bridge relations and quotes against original Markdown; no independent human review','cases':60,'multi_hop':20,'cross_document':20,'controls':20,'outside_old_fields':60,'authored_after_development_freeze':True,'frozen_implementation_sha256':freeze['implementation_sha256'],'cross_fact_design':'Two seven-document financial cycles and one six-document staffing/teaching cycle; each fact in two questions; cluster uncertainty accounts for shared evidence'},ensure_ascii=False,indent=2)+'\n')
print('Test curated and source-compiled:',len(rows))
