"""Agent-reviewed source curation; no retrieval outputs or selector inputs."""
import json
from pathlib import Path
from benchmark.evidence_v2 import normalized, occurrences, source_end
from benchmark.generalization_dataset import compile_dataset
from benchmark.retrieval_round import CORPUS, sha
from benchmark import investigation as inv

ROOT = Path(__file__).parent.parent
MANIFEST = inv.read_json(ROOT / 'split_manifest.json')
DOCS = list(MANIFEST['source_sha256'])
rows = []


def proof(index, start, end):
    document = DOCS[index]; raw = (CORPUS / document).read_text()
    text, mapping = normalized(raw); a = text.index(start); b = text.index(end, a) + len(end)
    quote = raw[mapping[a]:source_end(raw, mapping[b-1])]
    assert len(occurrences(text, normalized(quote)[0])) == 1
    return {'document': document, 'quote': quote}


def add(category, question, answer, field, evidence, bridge=''):
    rows.append({'category': category, 'question': question, 'expected_answer': answer,
                 'field': field, 'bridge': bridge, 'evidence': evidence})


M = 'multi-hop'; C = 'cross-document'; F = 'single-document factual'
add(M, 'Na ata de novembro de 2022, qual foi o novo valor da bolsa no projeto sobre desconexões do chatbot para o docente que relatou o terceiro aditivo do LDE?',
    'R$ 6.750,00, para João Paulo Pordeus.', 'scholarship_adjustment', [
    proof(0, 'o Prof. João Paulo Pordeus relatou o 3º Termo Aditivo', 'coordenado pelo Prof. Javam Machado.'),
    proof(0, "no Projeto intitulado: 'Uma Solução Inteligente", 'seis mil, setecentos e cinquenta reais); 4.')],
    'O relato do LDE identifica Pordeus; a lista de bolsas do outro projeto associa a ele o reajuste.')
add(M, 'Em novembro de 2023, que serviços podia oferecer a empresa júnior de Ciência da Computação vinculada ao mesmo professor responsável pela OCI renovada naquela reunião?',
    'Serviços de consultoria e soluções tecnológicas para diversas empresas.', 'offered_services', [
    proof(1, "projeto de extensão intitulado: 'Olimpíada Cearense", 'tutor do PET da Computação.'),
    proof(1, 'o projeto de extensão da Empresa Júnior do Curso', 'para as diversas empresas.')],
    'A OCI identifica Fernando Trinta; outro projeto vincula a empresa júnior ao mesmo docente e descreve seus serviços.')
add(M, 'Na reunião ordinária de novembro de 2024, qual o valor mensal da bolsa ReArte do professor que sugeriu retomar a discussão dos planos de ensino na reunião seguinte?',
    'R$ 11.500,00, para Angelo Brayner.', 'scholarship_value', [
    proof(2, 'o Prof. Angelo Brayner sugeriu que esse tema', 'na próxima reunião deste Colegiado.'),
    proof(2, 'O Prof. Angelo Brayner relatou sua bolsa', 'por um período de 12 meses.')],
    'A sugestão sobre planos identifica Angelo; outro item registra sua bolsa ReArte.')
add(M, 'Na ata ordinária de novembro de 2025, qual o valor da bolsa no projeto de integração biométrica destinada ao docente por cuja iniciativa a UFC Virtual filmou a celebração da Computação?',
    'R$ 3.000,00, para Fernando Trinta.', 'scholarship_value', [
    proof(3, 'A filmagem foi feita pela UFC Virtual', 'em parceria com o PET;'),
    proof(3, "o chefe relatou a bolsa vinculada ao projeto intitulado 'Pesquisa e desenvolvimento de sistema de integração", '(8 meses).')],
    'A iniciativa da filmagem identifica Fernando; outro item associa a ele a bolsa do sistema biométrico.')
add(M, 'Na extraordinária de 24/11/2025, qual posição inicial sobre a vaga aposentada havia defendido o professor agradecido publicamente por José Maria por viabilizar o consenso?',
    'A volta da vaga para Algoritmos, defendida por Victor Campos.', 'initial_position', [
    proof(4, 'o Prof. José Maria agradeceu publicamente ao Prof. Victor', 'se deve ao Prof. Victor.'),
    proof(4, 'o Prof. Victor considerou o que foi apresentado', 'está complicado para o grupo;')],
    'O agradecimento identifica Victor; um relato anterior registra sua posição inicial.')
add(M, 'Na extraordinária de 18/11/2025, qual setor de estudos foi sugerido pelo docente que argumentou que as vagas dos líderes antigos deveriam voltar aos seus grupos de origem?',
    'Teoria da Computação, sugerida por Rudini.', 'study_sector', [
    proof(5, 'o Prof. Rudini argumentou que jamais ousaria dizer', 'a grande falta que eles fariam aos seus grupos.'),
    proof(5, 'o Prof. Rudini relatou que se lembra da época', 'como setor de estudos para o concurso.')],
    'A defesa das vagas identifica Rudini; outra intervenção dele registra o setor sugerido.')
add(M, 'Na extraordinária de 11/11/2025, em qual grupo de pesquisa, segundo Javam, poderia atuar o candidato cuja formação foi realizada em telecomunicações e camadas de rede de baixa abstração?',
    'LSBD, para Alexandre Fernandes.', 'research_group', [
    proof(6, 'o Prof. João Paulo Pordeus fez um breve relato', 'com camadas de rede de mais baixa abstração.'),
    proof(6, 'E concluiu informando que, considerando sua área de atuação', 'com o grupo do LSBD.')],
    'A formação identifica Alexandre no relato de Pordeus; a intervenção de Javam associa o candidato ao LSBD.')
add(M, 'Em dezembro de 2020, qual pontuação foi reportada no parecer parcial apresentado pelo professor que também presidia a banca final de estágio probatório de César Lincoln?',
    '1205,4 pontos, no parecer sobre João Paulo Madeiro.', 'assessment_score', [
    proof(7, 'O quarto ponto de pauta foi a criação de banca', 'a banca foi aprovada por unanimidade.'),
    proof(7, 'O sétimo ponto de pauta foi um relato do parecer parcial', 'em itens relacionados às atividades do docente.')],
    'A banca identifica João Fernando; o parecer por ele apresentado registra a pontuação de Madeiro.')
add(M, 'Na ata de dezembro de 2021, qual era o público principal da especialização relatada pelo presidente da banca de progressão de Valéria Lelli?',
    'Professores do estado.', 'course_audience', [
    proof(8, 'a formação de banca de progressão de Adjunto I', 'Prof. Paulo Rego.'),
    proof(8, 'O ponto de pauta seguinte foi a aprovação da proposta de curso de especialização', 'público alvo principal professores do estado.')],
    'A banca identifica José Maria; outro item apresenta o curso por ele relatado e seu público.')
add(M, 'Na ata de dezembro de 2022, em qual centro de pesquisa ocorreria a licença de capacitação do professor associado à coordenação do LDAR?',
    'AT&T Labs-Research, em New York, USA.', 'training_destination', [
    proof(9, "o 1º Termo Aditivo ao projeto de P&D denominado 'LDAR", 'em parceria com a empresa Lenovo.'),
    proof(9, 'o pedido de afastamento para licença capacitação', 'no período de 01/04/2023 a 30/06/2023.')],
    'O LDAR identifica Javam; outra passagem registra sua licença e o centro de pesquisa.')

add(F, 'Qual carga horária total foi registrada para a Residência em Segurança Cibernética 2023/2025 na ata de novembro de 2022?',
    '576 horas, correspondentes a 36 créditos.', 'course_workload', [proof(0, 'o projeto pedagógico do Curso de Pósgraduação', 'a serem distribuídos em 18 meses.')])
add(F, 'Na ata de novembro de 2023, qual foi a contribuição mínima definida para as cestas natalinas dos terceirizados?',
    'R$ 50,00.', 'contribution_value', [proof(1, 'o chefe colocou em discussão as contribuições', 'no mínimo R$ 50,00 (cinquenta reais).')])
add(F, 'Na reunião ordinária de novembro de 2024, qual alternativa atendeu à demanda de Vlademiro e levou à retirada do pedido de remoção da pauta?',
    'Participação no PGD em teletrabalho com execução parcial.', 'administrative_alternative', [proof(2, 'Iniciado o diálogo entre o Colegiado e o servidor Vlademiro', 'retirar esse ponto da pauta da reunião.')])
add(F, 'Na ata ordinária de novembro de 2025, qual valor e duração foram aprovados para a bolsa de Eduardo Duarte no CIDDE?',
    'R$ 5.000,00 por 17 meses, a partir de novembro de 2025.', 'scholarship_value_duration', [proof(3, '27ª Matéria: Aprovação de bolsa', 'por unanimidade pelo Colegiado.')])
add(F, 'Qual vaga motivava o concurso discutido na reunião extraordinária de 24/11/2025?',
    'A vaga da professora Cláudia Linhares, aposentada recentemente.', 'vacancy_origin', [proof(4, 'a pauta única desta reunião', 'docente aposentada recentemente.')])
add(F, 'Na extraordinária de 18/11/2025, qual dia-limite Pablo corrigiu para o encaminhamento do concurso, em lugar de quarta-feira?',
    'Terça-feira da próxima semana.', 'submission_deadline', [proof(5, 'o Prof. Pablo Mayckon corrigiu a data-limite', 'e não quarta-feira.')])
add(F, 'Na extraordinária de 11/11/2025, quais motivos o interessado na remoção alegou à chefia?',
    'Motivos familiares.', 'transfer_motivation', [proof(6, 'Continuou informando que conversara com o interessado', 'tendo apenas alegado motivos familiares.')])
add(F, 'Na ata de dezembro de 2020, qual bolsa de graduação do LG-SMT estava prevista para Maurício de Moura dos Santos?',
    'R$ 900,00 por 12 meses.', 'student_scholarship', [proof(7, 'Além destas, estão previstas bolsas para alunos de graduação', 'por 12 meses.')])
add(F, 'Em dezembro de 2021, onde e quando seria realizada a confraternização lembrada por Fernando Trinta?',
    'Na Casa José de Alencar, a partir das 12h em 10/12/2021.', 'event_venue_time', [proof(8, 'O último ponto de pauta foi solicitado pelo Prof. Fernando Trinta', 'no dia 10/12/2021.')])
add(F, 'Na extraordinária de junho de 2022, quantos votos recebeu a proposta vencedora sobre CK0211 e o que ela determinava?',
    '12 votos; negar a anuência, justificar e sugerir uma nova disciplina com código CB.', 'vote_outcome', [proof(12, 'Proposta 2: Negar a anuência', 'contando também com 03 abstenções.')])

add(C, 'Compare os reajustes de João Paulo Pordeus no projeto sobre desconexões do chatbot em novembro de 2022 e no AI-CID em novembro de 2023: quais novos valores foram registrados?',
    'R$ 6.750,00 no primeiro e R$ 7.500,00 no segundo.', 'scholarship_comparison', [rows[0]['evidence'][1], proof(1, 'o Prof. João Paulo Pordeus relatou o 3o Termo Aditivo', 'ambas pelo mesmo período do projeto.')])
add(C, 'Compare a programação do WTSG aprovada em novembro de 2022 e em novembro de 2023: para quando estava previsto o evento em cada ocasião?',
    '09/12/2022; janeiro ou fevereiro de 2024.', 'event_schedule_comparison', [proof(0, "a Ação de Extensão 'WTSG", 'sob a coordenação da Profa. Rossana Andrade.'), proof(1, 'O supracitado docente continuou relatando a ação extensionista', 'em janeiro ou fevereiro de 2024.')])
add(C, 'Que valores mensais foram informados para Fabiane Gubert no ReArte em novembro de 2024 e para Kelvin Rodrigues no ABIN Connect em novembro de 2025?',
    'R$ 7.500,00 e R$ 1.000,00, respectivamente.', 'scholarship_comparison', [proof(2, 'uma bolsa para a Prof.ª Fabiane', 'por 12 meses;'), proof(3, 'Três bolsas vinculadas ao Projeto', 'valor mensal de R$ 1.000,00 (mil reais);')])
add(C, 'Qual orçamento para 2025 constava no aditivo CH-IA aprovado em novembro de 2024 e qual orçamento constava no projeto biométrico com a Akiyama em novembro de 2025?',
    'R$ 9.272.185,85 e R$ 635.520,00, respectivamente.', 'budget_comparison', [proof(2, '12ª Matéria: Aprovação de Termo Aditivo', 'para o ano de 2025'), proof(3, "O projeto, intitulado 'Pesquisa e desenvolvimento de sistema de integração", 'quinhentos e vinte reais).')])
add(C, 'Sobre o concurso da vaga de Cláudia Linhares, qual votação adiou a escolha do setor em 18/11/2025 e qual setor foi aprovado em 24/11/2025?',
    'O adiamento venceu por 11 a 9 votos; depois foi aprovado Algoritmos e Banco de Dados.', 'recruitment_decision_sequence', [proof(5, 'decidir o setor de estudos naquela reunião', 'da Proposta 1.'), proof(4, 'O Colegiado aprovou por unanimidade o setor de estudo', 'para o supracitado concurso.')])
add(C, 'Quantos votos apoiaram aproveitar imediatamente a vaga na reunião de 18/11/2025 e quem José Maria agradeceu por construir o consenso na reunião de 24/11/2025?',
    '12 votos; Victor Campos.', 'recruitment_vote_and_mediation', [proof(5, 'primeiramente, vamos decidir se aproveitamos', '7 votos da Proposta 2.'), rows[4]['evidence'][0]])
add(C, 'Que período de avaliações discentes foi consultado para a remoção discutida em 11/11/2025 e qual pontuação mínima de estágio probatório foi mencionada em dezembro de 2020?',
    'Os últimos cinco anos; 900 pontos.', 'assessment_requirements', [proof(6, 'o Prof. Pablo solicitara ao interessado os relatórios', 'suas notas são bastante altas.'), proof(7, 'Ressaltase que o candidato precisa', 'aprovação em seu estágio probatório.')])
add(C, 'Quais disciplinas recentes do candidato à remoção foram citadas na extraordinária de 11/11/2025 e qual nova disciplina foi aprovada em dezembro de 2020 por iniciativa de Javam?',
    'Processamento Digital de Sinais e Sistemas Lineares; Privacidade de Dados.', 'teaching_comparison', [proof(6, 'O Prof. Pablo também respondeu a terceira pergunta', 'Sistemas Lineares, entre outras.'), proof(7, 'O terceiro ponto de pauta foi a aprovação da criação', 'por iniciativa do professor Javam Machado.')])
add(C, 'Compare os destinos de pesquisa aprovados para Heron em dezembro de 2021 e para Javam em dezembro de 2022: quais instituições os receberiam?',
    'Khoury College of Computer Sciences of Northeastern University; AT&T Labs-Research.', 'research_destinations', [proof(8, 'a aprovação do afastamento do Prof. Heron', 'of Northeastern University.'), rows[9]['evidence'][1]])
add(C, 'Quais valores de bolsa para Javam foram registrados no CIDDE em dezembro de 2023 e no DHUNA em dezembro de 2025?',
    'R$ 8.000,00 e R$ 2.000,00, respectivamente.', 'scholarship_comparison', [proof(10, "o projeto de pesquisa: 'CIDDE", 'oito mil reais);'), proof(11, '6ª Matéria: Aprovação de bolsa', 'por unanimidade pelo Colegiado.')])

if __name__ == '__main__':
    inventory = inv.read_json(Path('benchmark/datasets/generalization_v1/inventory.json'))
    compile_dataset(rows, inventory, 'test', ROOT / 'test', expected_counts=MANIFEST['quotas'])
    inv.save_json(ROOT / 'test/source_audit.json', {'status': 'reviewed_against_markdown',
        'questions': len(rows), 'source_sha256': MANIFEST['source_sha256'],
        'annotation_method': 'agent source review; explicit indirect relation reviewed for each multi-hop; no retrieval consulted',
        'independent_human_review': False, 'automatic_draft_rejected': 'drafts/00.json preserved: project confusion, English question, missing bridge',
        'no_retrieval_results_used': True})
