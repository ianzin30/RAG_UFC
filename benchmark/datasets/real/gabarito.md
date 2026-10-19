# Gabarito — 80 questões reais

Gerado de `questions.json`. Revisão documental de 01/10/2026; nenhum resultado de execução do RAG está contido aqui. Veja [protocolo e limitações](README.md). As rubricas completas e erros críticos estão no JSON.

## single-document factual — 10 questões

### REAL-F01

Quem é o coordenador na instituição do projeto AFO?

**Gabarito:** Fernando Antonio Mota Trinta.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_NAME`.

### REAL-F02

Quais são as datas de início e término estimado do AFO II, na seção de duração do plano de trabalho?

**Gabarito:** Início em 01/03/2026 e término estimado em 28/02/2027.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_DATES`.

### REAL-F03

Qual ferramenta de Infrastructure as Code é citada no RACK como utilizada no provisionamento da infraestrutura do ciclo anterior?

**Gabarito:** Terraform.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_TOOLS`.

### REAL-F04

Quais três novas dimensões devem ser incorporadas às análises de uso e predição de capacidade do SAAR?

**Gabarito:** Aplicações, classes de usuários e casos de uso.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_DIMENSIONS`.

### REAL-F05

Na extraordinária de 13/07/2022, em que condições o Departamento aprovou a oferta de Fundamentos de Programação (CK0211) para a Licenciatura em Matemática noturna?

**Gabarito:** A oferta foi aprovada para o primeiro semestre de cada ano, no primeiro horário noturno, das 18h30 às 20h30. A condição de disponibilidade de professor foi rejeitada.

Fontes: [42_07-2022_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/42_07-2022_Ata_de_Reuniao_Extraordina_ria.md).

Trechos em `evidence.json`: `JULY22_DECISION`, `JULY22_VOTES`.

### REAL-F06

Na ata de 10/01/2025, qual data a DICON informou como correta para o fim do contrato de Matheus Santos, e quais eram a data solicitada e a data lançada por engano?

**Gabarito:** A data correta informada foi 31/01/2025; o Departamento havia solicitado 14/03/2025; a data lançada por engano era 08/08/2025.

Fontes: [06_01-2025_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/06_01-2025_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN25_CONTRACT`.

### REAL-F07

De qual campus viria Wladimir Araújo Tavares e qual foi a decisão sobre sua remoção na reunião de 21/06/2024?

**Gabarito:** Do Campus da UFC em Quixadá. O Colegiado aprovou por unanimidade sua remoção para o Departamento de Computação.

Fontes: [38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md).

Trechos em `evidence.json`: `JUNE24_TRANSFER`, `JUNE24_APPROVAL`.

### REAL-F08

Na reunião de 29/01/2024, de quanto para quanto foi revisto o orçamento do CIDDE?

**Gabarito:** De R$ 4.195.352,34 para R$ 3.516.108,71.

Fontes: [05_01-2024_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/05_01-2024_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN24_CIDDE`.

### REAL-F09

Em que data, horário e modalidade ocorreu a reunião registrada na ata 01-2026?

**Gabarito:** Em 30/01/2026, às 10h10, de forma inteiramente remota.

Fontes: [07_01-2026_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/07_01-2026_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN26_OPENING`.

### REAL-F10

Qual é a vigência prevista para o LDAR relatado na ata de 29/01/2024?

**Gabarito:** Dois anos, de 01/04/2024 a 31/03/2026.

Fontes: [05_01-2024_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/05_01-2024_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN24_LDAR`.

## entity lookup — 8 questões

### REAL-E01

Quem consta como coordenador na instituição do Storage Analytics and Auto-Reclamation II?

**Gabarito:** Lincoln Souza Rocha.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_NAME`.

### REAL-E02

Quem é o coordenador na instituição do projeto Rack Build Deployment Validation and Provisioning II?

**Gabarito:** Paulo Antonio Leal Rego.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_NAME`.

### REAL-E03

Quem informou ser o novo tutor do PET na ata de 19/08/2022, e para qual atividade pediu ajuda?

**Gabarito:** Fernando Trinta, que pediu ajuda dos professores nas maratonas de programação realizadas pelo PET.

Fontes: [49_08-2022_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/49_08-2022_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `PET`.

### REAL-E04

Quem presidiu a comissão julgadora do Edital 13/2025, aprovada em 21/02/2025, e quem era seu secretário?

**Gabarito:** A presidente era Emanuele Marques Rodrigues Santos e o secretário era Pablo Mayckon Silva Farias.

Fontes: [11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md).

Trechos em `evidence.json`: `FEB25_COMMISSION`.

### REAL-E05

Quem foi indicado como presidente da banca de Algoritmos e Banco de Dados, Edital 09/2025, na reunião de 30/01/2026?

**Gabarito:** Avelino Francisco Zorzo, da PUCRS.

Fontes: [07_01-2026_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/07_01-2026_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN26_BOARD`.

### REAL-E06

Quem coordenava o LDAR e qual empresa era parceira, conforme a ata de 29/01/2024?

**Gabarito:** Javam Machado, em parceria com a Lenovo Brasil.

Fontes: [05_01-2024_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/05_01-2024_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN24_LDAR`.

### REAL-E07

Qual é o nome completo da coordenadora do projeto de Web Semântica e Big Data da SEFAZ-MA na extraordinária de 14/03/2023?

**Gabarito:** Vânia Maria Ponte Vidal.

Fontes: [15_03-2023_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/15_03-2023_Ata_de_Reuniao_Extraordina_ria.md).

Trechos em `evidence.json`: `SEFAZ_2023`.

### REAL-E08

No plano do SAAR, a que se refere Storage Pillar e quais famílias são citadas?

**Gabarito:** São subdivisões do Dell Storage Team focadas em famílias de produtos de armazenamento: blocks, files e objects.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_PILLARS`.

## cross-document — 10 questões

### REAL-C01

Compare os coordenadores dos projetos AFO e RACK.

**Gabarito:** O AFO é coordenado por Fernando Antonio Mota Trinta; o RACK, por Paulo Antonio Leal Rego.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md); [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `AFO_NAME`, `RACK_NAME`.

### REAL-C02

Qual é a diferença de objeto entre AFO II, RACK II e SAAR II nos respectivos planos de trabalho?

**Gabarito:** AFO II automatiza o onboarding de aplicações no ambiente federado; RACK II valida e provisiona infraestrutura de data centers; SAAR II analisa, prevê e automatiza a utilização de armazenamento corporativo.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md); [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md); [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `AFO_OBJECTIVE`, `RACK_OBJECTIVE`, `SAAR_OBJECTIVE`.

### REAL-C03

Comparando somente os quadros de indicadores esperados do AFO e do SAAR, ambos assinalam publicação científica? O que cada um assinala para software e publicação?

**Gabarito:** Não. Ambos assinalam a geração de um software; o SAAR também assinala uma publicação científica, enquanto o item de publicações está desmarcado no AFO.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md); [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `AFO_INDICATORS`, `SAAR_INDICATORS`.

### REAL-C04

Como diferem as alterações do projeto SEFAZ-MA descritas nas atas de 19/08/2022 e 14/03/2023?

**Gabarito:** Em 19/08/2022, ampliou-se o valor para R$ 1.867.500,00 para incluir a Etapa II, fases 5, 6 e 7. Em 14/03/2023, prorrogou-se a vigência de 04/04/2023 a 03/07/2023 sem alterar o valor global.

Fontes: [49_08-2022_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/49_08-2022_Ata_de_Reuniao.md); [15_03-2023_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/15_03-2023_Ata_de_Reuniao_Extraordina_ria.md).

Trechos em `evidence.json`: `SEFAZ_2022`, `SEFAZ_2023`.

### REAL-C05

O que mudou na Residência em Segurança da Informação UFC/Samsung/SiDi nas atas de 19/08/2022 e 14/03/2023?

**Gabarito:** Em agosto de 2022, o valor passou de R$ 2.039.726,92 para R$ 2.101.943,01 para aquisição de softwares com preços atualizados. Em março de 2023, o término passou de 13/08/2023 para 31/08/2023.

Fontes: [49_08-2022_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/49_08-2022_Ata_de_Reuniao.md); [15_03-2023_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/15_03-2023_Ata_de_Reuniao_Extraordina_ria.md).

Trechos em `evidence.json`: `RESIDENCY_2022`, `RESIDENCY_2023`.

### REAL-C06

Compare a situação de Rafael da Silva Albuquerque nas seleções relatadas em 12/03/2025 e 05/09/2025. São resultados contraditórios da mesma seleção?

**Gabarito:** Em março, no Edital 13/2025, ele foi eliminado por reprovação na prova escrita. Em setembro, no Edital 106/2025, foi aprovado em segundo lugar. São seleções diferentes, portanto os registros não são contraditórios.

Fontes: [19_03-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/19_03-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md); [60_09-2025_Ata_de_Reuniao.pdf_Extraordinaria.md](../../../data/collections/uploaded_files/60_09-2025_Ata_de_Reuniao.pdf_Extraordinaria.md).

Trechos em `evidence.json`: `MAR25_EDITAL`, `MAR25_ELIMINATION`, `SEP25_EDITAL`, `SEP25_RESULT`.

### REAL-C07

Como João Paulo do Vale Madeiro é identificado na chefia nas aberturas das atas de 13/07/2022 e 29/01/2024?

**Gabarito:** Como subchefe em 13/07/2022 e como chefe em 29/01/2024.

Fontes: [42_07-2022_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/42_07-2022_Ata_de_Reuniao_Extraordina_ria.md); [05_01-2024_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/05_01-2024_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JULY22_CHAIR`, `JAN24_CHAIR`.

### REAL-C08

Qual função de chefia aparece associada a Fernando Trinta nas aberturas das atas de 04/09/2020 e 21/06/2024?

**Gabarito:** Chefe em 04/09/2020 e subchefe em 21/06/2024.

Fontes: [53_09-2020_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/53_09-2020_Ata_de_Reuniao.md); [38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md).

Trechos em `evidence.json`: `SEP20_CHAIR`, `JUNE24_CHAIR`.

### REAL-C09

As extraordinárias de 13/07/2022 e 21/06/2024 ocorreram na mesma modalidade?

**Gabarito:** Não. A de 13/07/2022 ocorreu por videoconferência; a de 21/06/2024 foi híbrida.

Fontes: [42_07-2022_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/42_07-2022_Ata_de_Reuniao_Extraordina_ria.md); [38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md).

Trechos em `evidence.json`: `JULY22_CHAIR`, `JUNE24_CHAIR`.

### REAL-C10

Segundo os quadros-resumo, qual projeto prevê mais horas totais, AFO ou SAAR, e qual é a diferença?

**Gabarito:** O AFO prevê 30.864 horas e o SAAR 21.600 horas. O AFO prevê 9.264 horas a mais.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md); [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `AFO_HOURS`, `SAAR_HOURS`.

## multi-hop — 10 questões

### REAL-H01

Qual é o nome do coordenador do projeto que prevê geração de token OAuth?

**Gabarito:** O projeto é o AFO II, cujo coordenador na instituição é Fernando Antonio Mota Trinta.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_OAUTH`, `AFO_NAME`.

Cadeia que precisa ser sustentada:

1. Geração de token OAuth identifica o AFO II.
2. AFO II tem Fernando Antonio Mota Trinta como coordenador.

### REAL-H02

Quem coordena o projeto cujo ciclo anterior automatizou a configuração de firmware via Redfish?

**Gabarito:** Paulo Antonio Leal Rego, coordenador do RACK II.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_TOOLS`, `RACK_NAME`.

Cadeia que precisa ser sustentada:

1. A automação de firmware via Redfish identifica RACK.
2. O coordenador institucional do RACK é Paulo Antonio Leal Rego.

### REAL-H03

Quem é o coordenador do projeto que prevê expandir seu ETL para Unity, PowerScale e PowerFlex?

**Gabarito:** Lincoln Souza Rocha, coordenador do SAAR II.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_PRODUCTS`, `SAAR_NAME`.

Cadeia que precisa ser sustentada:

1. Os três produtos aparecem na expansão de integração do SAAR.
2. O coordenador do SAAR é Lincoln Souza Rocha.

### REAL-H04

Qual função no PET o coordenador do AFO declarou ter assumido na ata de 19/08/2022, e para que pediu colaboração?

**Gabarito:** Fernando Trinta, coordenador do AFO, informou ser o novo tutor do PET e pediu ajuda dos professores nas maratonas de programação do PET.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md); [49_08-2022_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/49_08-2022_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `AFO_NAME`, `PET`.

Cadeia que precisa ser sustentada:

1. AFO → Fernando Antonio Mota Trinta.
2. Fernando Trinta → novo tutor do PET e ajuda nas maratonas em 2022.

### REAL-H05

De qual classe para qual classe era a progressão do coordenador do RACK relatada em 19/08/2022, e quem apresentou o parecer?

**Gabarito:** Paulo Antônio Leal Rego: de Professor Adjunto C II para Professor Adjunto C III. Lincoln Rocha apresentou o parecer favorável.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md); [49_08-2022_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/49_08-2022_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `RACK_NAME`, `REGO_PROGRESSION`.

Cadeia que precisa ser sustentada:

1. RACK → Paulo Antonio Leal Rego.
2. Paulo Rego → progressão C II a C III, relatada por Lincoln Rocha.

### REAL-H06

Por que o coordenador do SAAR estava exercendo a chefia na reunião de 30/01/2026?

**Gabarito:** O coordenador do SAAR é Lincoln Souza Rocha. Na reunião ele estava como subchefe em exercício da chefia devido às férias do chefe Pablo Mayckon.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md); [07_01-2026_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/07_01-2026_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `SAAR_NAME`, `JAN26_CHAIR`.

Cadeia que precisa ser sustentada:

1. SAAR → Lincoln Souza Rocha.
2. Lincoln exercia a chefia por causa das férias de Pablo Mayckon.

### REAL-H07

O projeto da SEFAZ-MA cuja vigência foi prorrogada até 03/07/2023 já havia recebido qual novo valor global na ata de 19/08/2022?

**Gabarito:** O projeto de Web Semântica e Big Data da SEFAZ-MA havia passado a R$ 1.867.500,00 em agosto de 2022. A prorrogação de 2023 não alterou o valor global.

Fontes: [15_03-2023_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/15_03-2023_Ata_de_Reuniao_Extraordina_ria.md); [49_08-2022_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/49_08-2022_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `SEFAZ_2023`, `SEFAZ_2022`.

Cadeia que precisa ser sustentada:

1. A data 03/07/2023 identifica a prorrogação do projeto SEFAZ-MA.
2. O aditivo de 2022 fixou o novo valor em R$ 1.867.500,00.

### REAL-H08

Quem era o secretário da comissão do Edital 13/2025 e qual disciplina ele assumiu, como chefe, na distribuição de 2026/1 registrada em 30/01/2026?

**Gabarito:** Pablo Mayckon Silva Farias. Assumiu Programação Computacional para Engenharia/03A (CK0270), para Engenharia Civil; Rudini Sampaio se dispôs a ajudá-lo.

Fontes: [11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md); [07_01-2026_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/07_01-2026_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `FEB25_COMMISSION`, `JAN26_CHAIR`, `JAN26_TEACHING`.

Cadeia que precisa ser sustentada:

1. Secretário da comissão → Pablo Mayckon.
2. O chefe titular mencionado na ata de 2026 é Pablo Mayckon.
3. O chefe assumiu CK0270 e Rudini ofereceu ajuda.

### REAL-H09

Qual era a data de término do afastamento da docente que presidiu a comissão do Edital 13/2025, segundo a explicação da DICON registrada em 10/01/2025?

**Gabarito:** A presidente era Emanuele Marques Rodrigues Santos. Seu afastamento terminaria em 31/01/2025, data que a DICON informou como correta também para o término do contrato do substituto.

Fontes: [11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md); [06_01-2025_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/06_01-2025_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `FEB25_COMMISSION`, `JAN25_CONTRACT`.

Cadeia que precisa ser sustentada:

1. Presidente do Edital 13/2025 → Emanuele Marques Rodrigues Santos.
2. Afastamento de Emanuele terminaria em 31/01/2025.

### REAL-H10

Em que posição ficou, no resultado de 05/09/2025, o candidato que havia sido eliminado na prova escrita da seleção relatada em 12/03/2025?

**Gabarito:** Rafael da Silva Albuquerque foi aprovado em segundo lugar na seleção relatada em 05/09/2025.

Fontes: [19_03-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/19_03-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md); [60_09-2025_Ata_de_Reuniao.pdf_Extraordinaria.md](../../../data/collections/uploaded_files/60_09-2025_Ata_de_Reuniao.pdf_Extraordinaria.md).

Trechos em `evidence.json`: `MAR25_ELIMINATION`, `SEP25_RESULT`.

Cadeia que precisa ser sustentada:

1. Eliminado na escrita em março → Rafael da Silva Albuquerque.
2. Rafael → segundo colocado e aprovado em setembro.

## list/aggregation — 8 questões

### REAL-L01

Quais produtos de armazenamento são nominalmente listados no item de extensão da integração do SAAR?

**Gabarito:** Unity, PowerScale (Isilon) e PowerFlex. O texto também menciona outros, sem nomeá-los nesse item.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_PRODUCTS`.

### REAL-L02

Liste os quatro eixos da Frente 2 do RACK II e dê uma característica de cada um.

**Gabarito:** Suporte a novos dispositivos, como Power Max e HDA; Versioning System, com rollback e histórico; Workflow-like Automation, com orquestração por plataforma como N8N; Front-End Development, com dashboard de status, erros, tarefas e métricas.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_DEVICES`, `RACK_VERSIONING`, `RACK_WORKFLOW`, `RACK_FRONTEND`.

### REAL-L03

Quais são os dois itens da seção 'Novos módulos funcionais' do AFO II?

**Gabarito:** Geração de Token OAuth Token; Observabilidade e Auditabilidade.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_OAUTH`, `AFO_OBSERVABILITY`.

### REAL-L04

Liste os membros efetivos e suplentes da banca de Algoritmos e Banco de Dados aprovada em 30/01/2026, indicando quem é o presidente.

**Gabarito:** Efetivos: Avelino Francisco Zorzo, presidente, Flávio Keidi Miyazawa e Daniel Cardoso Moraes de Oliveira. Suplentes: Fábio Protti e Valéria Cesário Times Alves.

Fontes: [07_01-2026_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/07_01-2026_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN26_BOARD`.

### REAL-L05

Qual foi a composição completa, com funções, da comissão da seleção de Fundamentos de Programação aprovada em 21/02/2025?

**Gabarito:** Emanuele Marques Rodrigues Santos, presidente; João Bosco Ferreira Filho e João Paulo do Vale Madeiro, membros; Fernando Antonio Mota Trinta, suplente; Pablo Mayckon Silva Farias, secretário.

Fontes: [11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md).

Trechos em `evidence.json`: `FEB25_COMMISSION`.

### REAL-L06

Quais foram os resultados das três votações sobre CK0211 em 13/07/2022?

**Gabarito:** A anuência foi aprovada por unanimidade, sem votos contrários. Condicionar ao horário 18h30–20h30 teve 14 votos favoráveis e 3 contrários. Condicionar à disponibilidade de professor teve 7 favoráveis e 10 contrários, sendo rejeitado.

Fontes: [42_07-2022_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/42_07-2022_Ata_de_Reuniao_Extraordina_ria.md).

Trechos em `evidence.json`: `JULY22_VOTES`.

### REAL-L07

Somando os totais de pessoas previstos nos quadros-resumo de AFO e SAAR, quantas alocações nos dois projetos são previstas? Isso prova quantas pessoas distintas participarão?

**Gabarito:** AFO prevê 27 e SAAR 21, somando 48 alocações. A soma não prova que sejam 48 pessoas distintas, pois os quadros não permitem excluir participação da mesma pessoa em ambos.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md); [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `AFO_PEOPLE`, `SAAR_PEOPLE`.

### REAL-L08

Quais quatro bolsas do Automated Parts Management – Fase IV foram aprovadas na ata de 29/01/2024, com beneficiário, valor e período?

**Gabarito:** Paulo Rego: R$ 7.000,00; Fernando Trinta: R$ 5.000,00; César Lincoln: R$ 5.000,00; Leonardo Costa: R$ 3.000,00. Todas por 12 meses, de 02/2024 a 01/2025.

Fontes: [05_01-2024_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/05_01-2024_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN24_APM_GRANTS`.

## summary — 6 questões

### REAL-S01

Resuma as melhorias e novas funcionalidades previstas para o SAAR.

**Gabarito:** As melhorias incluem ampliar a integração ETL com produtos Dell, enriquecer as análises, estruturar a auto-reclamação e dar suporte a produção com DevOps/CI/CD. As novas funcionalidades são registro de ações, métricas de processamento e um dashboard consolidado de observabilidade.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_PRODUCTS`, `SAAR_DIMENSIONS`, `SAAR_RULES`, `SAAR_DEVOPS`, `SAAR_LOGS`, `SAAR_METRICS`, `SAAR_DASHBOARD`.

### REAL-S02

Resuma a passagem do primeiro ciclo FY26 para o FY27 no AFO II, distinguindo o que já havia sido desenvolvido do que foi priorizado para o segundo ciclo.

**Gabarito:** O FY26 entregou um MVP com solicitações de implantação, validações automatizadas e integração ao Oracle Identity and Access Management. Para FY27 foram priorizados tokens OAuth, a conclusão da automação ponta a ponta e a ampliação de integração, observabilidade, autenticação e auditoria.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_MVP`, `AFO_FY27`.

### REAL-S03

Resuma as duas frentes do RACK II e explique como as novas capacidades complementam os módulos existentes.

**Gabarito:** A primeira frente otimiza validação, integração e provisionamento, com desempenho, testes e estabilidade. A segunda amplia dispositivos, versiona configurações, orquestra workflows e cria uma interface gráfica, ampliando rastreabilidade, automação e operação da solução.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_CORE`, `RACK_INTEGRATION`, `RACK_PROVISIONING`, `RACK_DEVICES`, `RACK_VERSIONING`, `RACK_WORKFLOW`, `RACK_FRONTEND`.

### REAL-S04

Resuma a preocupação com a carga didática do novo curso de Ciência de Dados e a decisão final sobre CK0211 na extraordinária de 13/07/2022.

**Gabarito:** O novo curso previa 13 disciplinas novas e mais 7 existentes, totalizando 20 obrigatórias sob responsabilidade do Departamento. Apesar da preocupação com carga didática, aprovou-se CK0211 no primeiro semestre de cada ano, das 18h30 às 20h30, sem condicioná-la à disponibilidade de professor.

Fontes: [42_07-2022_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/42_07-2022_Ata_de_Reuniao_Extraordina_ria.md).

Trechos em `evidence.json`: `JULY22_LOAD`, `JULY22_DECISION`, `JULY22_VOTES`.

### REAL-S05

Resuma os dois assuntos centrais tratados na extraordinária de 21/06/2024, distinguindo deliberação de apresentação e debate.

**Gabarito:** O Colegiado aprovou por unanimidade a remoção de Wladimir Tavares de Quixadá para o Departamento. Depois, Yuri Lenon apresentou e debateu dados da avaliação institucional de 2023/1 e 2023/2, no contexto do plano de melhoria do NDE e de um seminário aos alunos.

Fontes: [38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md).

Trechos em `evidence.json`: `JUNE24_TRANSFER`, `JUNE24_APPROVAL`, `JUNE24_SEMINAR`, `JUNE24_DEBATE`.

### REAL-S06

A extraordinária de 24/11/2023 terminou aprovando a mudança de João Paulo Pordeus para 20 horas? Resuma a solução efetivamente aprovada.

**Gabarito:** Não. O pedido evoluiu para licença de interesses particulares de três anos, sem remuneração. O Colegiado aprovou a licença por unanimidade e a imediata solicitação de seleção de substituto em Inteligência Artificial/Fundamentos de Programação.

Fontes: [71_11-2023_Ata_de_Reuniao_Extraordinaria.md](../../../data/collections/uploaded_files/71_11-2023_Ata_de_Reuniao_Extraordinaria.md).

Trechos em `evidence.json`: `NOV23_CHANGE`, `NOV23_DECISION`.

## spreadsheet/table — 8 questões

### REAL-T01

No quadro-resumo de recursos humanos do AFO, quantas pessoas estão previstas em RH direto superior, RH direto médio e RH indireto superior, e qual é o total?

**Gabarito:** 17 em RH direto superior, 9 em RH direto médio e 1 em RH indireto superior; total de 27.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_PEOPLE`.

### REAL-T02

No quadro-resumo financeiro do AFO, quais são o total de dispêndios, o valor de RH Total e o valor e percentual de Equipamento e Software?

**Gabarito:** Total de dispêndios: R$ 2.130.184,82. RH Total: R$ 1.661.931,78. Equipamento e Software: R$ 52.300,00, correspondentes a 2,46%.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_TOTAL`, `AFO_RH`, `AFO_EQUIPMENT`.

### REAL-T03

Quais totais de pessoas e horas trabalhadas constam no quadro-resumo do SAAR?

**Gabarito:** 21 pessoas e 21.600 horas trabalhadas.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_PEOPLE`, `SAAR_HOURS`.

### REAL-T04

A soma das parcelas de horas do quadro-resumo do RACK coincide com o total impresso? Informe a soma, o total impresso e a diferença, sem corrigir silenciosamente o documento.

**Gabarito:** Não. 10.800 + 8.400 + 1.920 = 21.120 horas, mas a tabela imprime 21.200 horas. O total impresso é 80 horas maior. A inconsistência é do quadro consultado e não permite decidir qual número deveria ser corrigido.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_HOURS`.

### REAL-T05

No cronograma de gastos do RACK, qual é a redução do RH Direto previsto de março para abril de 2026?

**Gabarito:** De R$ 90.779,76 em março para R$ 84.629,72 em abril: redução de R$ 6.150,04.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_MONTHS`, `RACK_MONTH_RH`.

### REAL-T06

Na parte de março a setembro de 2026 do cronograma do RACK, em qual mês aparece o lançamento de Equipamentos e software e qual é o valor?

**Gabarito:** Em março de 2026, R$ 31.300,00. As demais células desse trecho estão em branco.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_MONTHS`, `RACK_MONTH_EQUIPMENT`.

### REAL-T07

Quais quantidades de software e publicação científica o quadro de indicadores do SAAR espera gerar, e os dois itens estão marcados?

**Gabarito:** Um software e uma publicação científica; ambos estão marcados com x.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_INDICATORS`.

### REAL-T08

O quadro-resumo do AFO informa um valor numérico para Viagens? Uma célula vazia permite afirmar que o gasto efetivamente realizado foi zero?

**Gabarito:** Não há valor preenchido na linha Viagens. Uma célula vazia em um orçamento previsto não comprova gasto efetivamente realizado de zero.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_TRAVEL_EMPTY`.

## unanswerable — 10 questões

### REAL-U01

Qual é o CPF do coordenador do AFO?

**Gabarito:** Não é possível informar o CPF do coordenador do AFO com a evidência disponível. O nome do coordenador não supre o dado solicitado.

Contexto para revisão da insuficiência: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_NAME`.

### REAL-U02

Segundo o plano de trabalho do AFO II, em que dia a solução efetivamente entrou em produção?

**Gabarito:** O plano descreve entregas e datas previstas, mas não comprova a data em que a solução efetivamente entrou em produção.

Contexto para revisão da insuficiência: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_DATES`, `AFO_DELIVERY`.

### REAL-U03

Quantos terabytes o SAAR II já recuperou em produção, segundo seu plano de trabalho?

**Gabarito:** O plano prevê métricas de volume recuperado, mas não fornece um resultado efetivamente medido em terabytes.

Contexto para revisão da insuficiência: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_METRICS`.

### REAL-U04

Qual latência p95, em milissegundos, o motor de provisionamento do RACK II atingiu em produção, segundo o plano?

**Gabarito:** O plano prevê otimização de desempenho, mas não informa uma medição de latência p95 em produção.

Contexto para revisão da insuficiência: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_PROVISIONING`.

### REAL-U05

Quais notas cada candidato recebeu no concurso de Algoritmos e Banco de Dados, Edital 09/2025, segundo a ata de 30/01/2026?

**Gabarito:** Essa ata aprova a composição da banca; não apresenta notas de candidatos do concurso.

Contexto para revisão da insuficiência: [07_01-2026_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/07_01-2026_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN26_BOARD`.

### REAL-U06

Usando somente o texto extraído de neymar.jpg disponível na coleção, qual é o número da camisa da pessoa retratada?

**Gabarito:** O texto extraído contém apenas CBF e BRASIL, além do nome do arquivo, e não informa número de camisa.

Contexto para revisão da insuficiência: [86_neymar.md](../../../data/collections/uploaded_files/86_neymar.md).

Trechos em `evidence.json`: `IMAGE_TEXT`.

### REAL-U07

Qual é o valor literal de um token OAuth de produção informado no plano AFO II?

**Gabarito:** O plano descreve geração e armazenamento de tokens, mas não fornece um valor literal de token de produção.

Contexto para revisão da insuficiência: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_OAUTH`.

### REAL-U08

A ata de 21/06/2024 traz um mapa nominal de votação, com o voto individual de cada professor sobre a remoção de Wladimir? Transcreva esse mapa se existir.

**Gabarito:** Não há mapa nominal de votos nessa ata. Ela registra aprovação por unanimidade, sem discriminar individualmente os votos.

Contexto para revisão da insuficiência: [38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/38_06-2024_Ata_de_Reuniao.pdf_Extraordina_ria.md).

Trechos em `evidence.json`: `JUNE24_APPROVAL`.

### REAL-U09

Qual é o DOI da publicação científica prevista como resultado do SAAR II?

**Gabarito:** O plano prevê uma publicação científica, mas não identifica um DOI para ela.

Contexto para revisão da insuficiência: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_INDICATORS`.

### REAL-U10

Quem é o coordenador do projeto?

**Gabarito:** É necessário esclarecer qual projeto: a coleção contém, por exemplo, AFO, RACK e SAAR, com coordenadores diferentes.

Contexto para revisão da insuficiência: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md); [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md); [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `AFO_NAME`, `RACK_NAME`, `SAAR_NAME`.

## follow-up conversational — 10 questões

### REAL-Q01

E quem coordena esse projeto na instituição?

Histórico fixo:

- Usuário: Fale sobre o projeto AFO.
- Assistente: O AFO automatiza o onboarding federado.

**Gabarito:** Fernando Antonio Mota Trinta coordena o AFO.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md).

Trechos em `evidence.json`: `AFO_NAME`.

### REAL-Q02

E o SAAR tem o mesmo período previsto?

Histórico fixo:

- Usuário: Qual é a duração prevista do AFO II?
- Assistente: De 01/03/2026 a 28/02/2027.

**Gabarito:** Sim. O SAAR também tem início em 01/03/2026 e término estimado em 28/02/2027, como o AFO.

Fontes: [85_AFO.md](../../../data/collections/uploaded_files/85_AFO.md); [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `AFO_DATES`, `SAAR_DATES`.

### REAL-Q03

Nesse controle de versões, o que se prevê além de manter um histórico?

Histórico fixo:

- Usuário: Quais recursos novos o RACK II prevê?
- Assistente: Entre eles estão novos dispositivos, controle de versões, workflows e uma interface gráfica.

**Gabarito:** No RACK, o Versioning System prevê rollback e ramificações para baselines e padrões de validação, com operações similares às de sistemas Git.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_VERSIONING`.

### REAL-Q04

E o painel de observabilidade dele deve reunir o quê?

Histórico fixo:

- Usuário: O que é o SAAR?
- Assistente: É a plataforma de análise de armazenamento e auto-reclamação descrita no plano de trabalho.

**Gabarito:** O dashboard do SAAR deve consolidar logs e estatísticas dos componentes, dando transparência e auditoria ao ciclo de análise e recuperação.

Fontes: [88_SAAR.md](../../../data/collections/uploaded_files/88_SAAR.md).

Trechos em `evidence.json`: `SAAR_DASHBOARD`.

### REAL-Q05

Essa licença era remunerada e por quanto tempo foi aprovada?

Histórico fixo:

- Usuário: O que foi decidido sobre João Paulo Pordeus em 24/11/2023?
- Assistente: Foi aprovada uma licença para tratar de interesses particulares.

**Gabarito:** Não era remunerada e foi aprovada por três anos. Uma possível prorrogação não significa que seis anos tenham sido aprovados.

Fontes: [71_11-2023_Ata_de_Reuniao_Extraordinaria.md](../../../data/collections/uploaded_files/71_11-2023_Ata_de_Reuniao_Extraordinaria.md).

Trechos em `evidence.json`: `NOV23_CHANGE`, `NOV23_DECISION`.

### REAL-Q06

E ficou dependendo de haver professor disponível? Qual foi a votação dessa condição?

Histórico fixo:

- Usuário: A oferta de CK0211 para a Matemática noturna foi aprovada em 13/07/2022?
- Assistente: Sim, para o primeiro semestre de cada ano, das 18h30 às 20h30.

**Gabarito:** Não. A condição de disponibilidade de professor foi rejeitada por 10 votos contrários e 7 favoráveis.

Fontes: [42_07-2022_Ata_de_Reuniao_Extraordina_ria.md](../../../data/collections/uploaded_files/42_07-2022_Ata_de_Reuniao_Extraordina_ria.md).

Trechos em `evidence.json`: `JULY22_VOTES`.

### REAL-Q07

Quando seria a prova escrita dessa seleção e a que horas seriam divulgadas as notas?

Histórico fixo:

- Usuário: Estou consultando a comissão de Fundamentos de Programação do Edital 13/2025, aprovada em 21/02/2025.
- Assistente: Certo, a ata extraordinária de fevereiro trata dessa comissão e do calendário da seleção.

**Gabarito:** Em 24/02/2025, das 08h às 12h; divulgação das notas da prova escrita às 14h55.

Fontes: [11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md](../../../data/collections/uploaded_files/11_02-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md).

Trechos em `evidence.json`: `FEB25_SCHEDULE`.

### REAL-Q08

De qual instituição é o presidente dela?

Histórico fixo:

- Usuário: Quero saber sobre a banca de Algoritmos e Banco de Dados aprovada em 30/01/2026.
- Assistente: A ata registra três membros efetivos e dois suplentes para essa banca.

**Gabarito:** Avelino Francisco Zorzo, presidente da banca, é da Pontifícia Universidade Católica do Rio Grande do Sul, PUCRS.

Fontes: [07_01-2026_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/07_01-2026_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN26_BOARD`.

### REAL-Q09

Então de quanto foi a redução?

Histórico fixo:

- Usuário: Como mudou o orçamento do CIDDE na ata de 29/01/2024?
- Assistente: Passou de R$ 4.195.352,34 para R$ 3.516.108,71.

**Gabarito:** A redução do orçamento do CIDDE foi de R$ 679.243,63.

Fontes: [05_01-2024_Ata_de_Reuniao.md](../../../data/collections/uploaded_files/05_01-2024_Ata_de_Reuniao.md).

Trechos em `evidence.json`: `JAN24_CIDDE`.

### REAL-Q10

Quem coordena esse último na instituição?

Histórico fixo:

- Usuário: Vamos falar sobre o AFO.
- Assistente: O AFO trata de onboarding federado.
- Usuário: Agora mude para o RACK.
- Assistente: Certo, passamos ao projeto de validação e provisionamento de racks.

**Gabarito:** Paulo Antonio Leal Rego coordena o RACK.

Fontes: [87_RACK.md](../../../data/collections/uploaded_files/87_RACK.md).

Trechos em `evidence.json`: `RACK_NAME`.
