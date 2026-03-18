# AFO.pdf

Extraction method: docling-puro

## PROJETO DE PESQUISA E DESENVOLVIMENTO Plano de Trabalho

## Projeto

AFO - Automation of Federation Onboarding II

## Coordenador na Instituição

Fernando Antonio Mota Trinta

<!-- image -->

## Empresa

## Instituição

Universidade Federal do Ceará - UFC Fundação de Apoio a Serviços Técnicos, Ensino e Fomento a Pesquisas - ASTEF

Outubro/2025

## 1. Classificação do Projeto

## 1.1. Tipo do Projeto

Hardware

☐

- [ ] Hardware com software embarcado ☐

- [ ] Melhoria de Processo Produtivo ☐

Software

x

- [ ] Software Aplicativo ☐

- [ ] Formação e Capacitação Profissional ☐

Outro

☐

Especificação: aplicável apenas se outros tipos

## 1.2. Área de Aplicação do Projeto

- J.62 - Atividades dos serviços de tecnologia da informação

## 1.3. Enquadramento Atividades do Projeto conforme art. 2º, Decreto nº 10.356/2020, alterado pelo Decreto nº 10.602/2021

|    | I - pesquisa básica - pesquisa experimental ou teórica executada primariamente para a aquisição de conhecimento novo sobre os fundamentos subjacentes aos fenômenos e fatos observáveis, sem qualquer aplicação particular ou uso em vista;               |
|----|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| X  | II - pesquisa aplicada - pesquisa original realizada para adquirir conhecimento e que se dirige primariamente a um objetivo ou a um alvo prático específico;                                                                                              |
|    | III - desenvolvimento experimental - trabalho sistemático, baseado em conhecimento preexistente e destinado à produção de novos produtos e processos ou ao aperfeiçoamento dos produtos e processos existentes;                                           |
|    | IV - inovação tecnológica - a implementação de produto, quer seja ele bem ou serviço, ou processo tecnológico novo, ou significativamente aprimorado, nos termos do disposto no inciso IV do caput do art. 2º da Lei nº 10.973, de 2 de dezembro de 2004; |

## 2. Descrição do Projeto de Pesquisa e Desenvolvimento

## 2.1. Introdução

Os  processos  de  autenticação  e  autorização  em  ambientes  federados  são  críticos  para  a segurança e o funcionamento dos sistemas corporativos da Dell. No contexto do Federal Auth Environment ,  o  processo  de  implantação ( onboarding )  de  aplicações e  que  consiste  na inclusão de novos sistemas e serviços à federação, ainda exige alto grau de intervenção manual, o que aumenta o risco de erros, alonga prazos de entrega e dificulta a escalabilidade.

O projeto Automation of Federation Onboarding (AFO) surgiu com o objetivo de transformar esse processo, desenvolvendo um sistema capaz de automatizar e orquestrar todas as etapas de integração de aplicações à federação, desde a submissão até a implantação em produção. Durante o primeiro ciclo (FY26), o projeto concentrou-se na entrega do MVP , que implementou os  módulos  principais  para  gerenciamento  de  solicitações  de  implantação,  automação  de validações  e  integração  com  o  ambiente Oracle  Identity  and  Access  Management .  Essa primeira  fase  estabeleceu  a  base  de  automação,  integrando  o  processo  de  submissão  de requisições e as validações iniciais, além de preparar o ambiente para adoção de práticas de DevOps 360 e DDC Standards .

Durante  o  primeiro  ciclo,  também  ocorreu  uma  importante  mudança  de escopo geral, com o surgimento  do OAuth  Token como  um  requisito  crítico  para  o  processo  de  onboarding  de aplicações.  Essa  necessidade  passou  a  ter  papel  central  a  ser  priorizada  em  um  segundo ciclo( FY27 ),  com  o  objetivo  de  fortalecer  o  controle  de  acesso  e  aprimorar  a  segurança  das integrações entre sistemas.  Além  disto,  neste  segundo  ciclo,  o AFO  II completará  a automação ponta a ponta do processo de implantação , além de ampliar as capacidades de integração e observabilidade e incorporar novos  módulos  de  autenticação  e auditoria, consolidando-se com isso, em uma solução completa, escalável e segura.

## 2.2. Objetivo e Escopo

Aprimorar e expandir o sistema Automation of Federation Onboarding (AFO) , completando o ciclo  de  automação  do  processo de onboarding de aplicações no ambiente federado da Dell, com ênfase em eficiência, conformidade e observabilidade.

## Escopo do Projeto

O escopo do AFO II (FY27) compreende duas frentes principais: ( i ) melhorias nos módulos desenvolvidos (Improvement Modules) e ( ii ) novas funcionalidades (New Feature Modules) , conforme detalhado a seguir. A primeira frente buscará complementar módulos que já foram  iniciados  no primeiro ciclo e que serão refinados no próximo ano, enquanto a segunda frente  traz  um  conjunto  novo de módulos para aprimorar ainda mais a solução automatizada. Mais detalhes sobre estas duas frentes são vistas a seguir:

## Melhorias nos módulos desenvolvidos

- Módulo de Implantação Automatizado: Serão realizadas atividades necessárias para completar a  automação  do  fluxo  de  implantação  no  Oracle  Identity  and  Access Management,  implementando  a  execução  ponta  a  ponta  e validando a conformidade

contínua com os padrões NIST 800-171 e CMMC ;

- Suporte  à  Produção  e  Práticas  DevOps: Será  consolidado  o suporte para deploys automatizados  e  integração  com pipelines de CI/CD ,  garantindo  transições  seguras e repetíveis entre ambientes de teste e produção;
- Módulo  de  Requisições: A  interface  de  requisições  será  expandida  para  permitir integrações  externas  e  validações  avançadas,  garantindo  que  todos  os  dados  de implantação atendam aos requisitos operacionais e de compliance.

## Novos módulos funcionais

- Geração de Token OAuth Token: Uma  interface unificada será projetada e implementada  para  suporte  à  criação  e  gerenciamento  de  domínios,  servidores  e clientes.  Dentre  suas  funções,  incluem-se  a  geração  e  armazenamento  seguro  de tokens e a integração com o sistema de requisições já existente;
- Observabilidade e Auditabilidade: Dada a importância no monitoramento da solução, serão criados dashboards avançados de observabilidade e auditoria com a consolidação de logs, métricas e rastros de execução. Também será permitido o  acompanhamento de desempenho, taxas de sucesso, gargalos e transparência das decisões automatizadas.

Esses  módulos  formarão  um  sistema  integrado,  que  reforça  a  automação  do  fluxo  de implantação,  e  amplia  a  visibilidade  operacional,  contribuindo  para  a  elevação  do  nível  de segurança e governança do processo federado.

## 2.3. Problemática Científico-Tecnológica

O  processo  de autenticação  federada é  um  componente  essencial  para  a  segurança  de sistemas  corporativos,  permitindo  o  gerenciamento  centralizado  de  identidade  e  acesso  em múltiplos ambientes. No ecossistema da Dell, esse processo é sustentado pelo Federal Auth (Oracle Identity and Access Management) , responsável por autenticar usuários e aplicações em ambientes críticos e regulados.

Atualmente, a implantação de aplicações nesse ambiente ainda apresenta forte dependência de  tarefas  manuais  -  como  a  coleta,  validação  e  transferência  de  dados  de  integração -, tornando o processo lento, suscetível a falhas humanas e difícil de escalar . Mesmo com os avanços conquistados no primeiro ciclo do projeto AFO  (Automation of Federation Onboarding) ,  o  fluxo  ainda  exige  intervenções  frequentes  de  administradores,  coordenação entre  equipes  distribuídas  e  verificação  manual  de  conformidade  com  normas  de  segurança como NIST 800-171 e CMMC .

A problemática científica deste projeto concentra-se na automação completa do processo de integração de aplicações à federação , com ênfase em  segurança, conformidade e rastreabilidade.  O  desafio  é  desenvolver  uma  arquitetura capaz de executar o processo de onboarding ponta  a  ponta ,  da  submissão  à  implantação  em  produção,  com  validações automatizadas de segurança, aprovações eletrônicas e orquestração entre múltiplos sistemas.

Do ponto de vista técnico, o projeto aborda três desafios principais:

1. Padronização  e  automação  de  fluxos  de  aprovação  e  implantação ,  reduzindo  a necessidade de coordenação entre equipes e eliminando gargalos operacionais.
2. Implementação de  módulos  inteligentes  de  observabilidade  e  auditabilidade , capazes de rastrear solicitações, logs e decisões, oferecendo transparência e suporte à conformidade.
3. Integração  de  novos  módulos  funcionais ,  como  o gerador  de tokens OAuth ,  que permitirá  o  controle  seguro  de  domínios,  recursos  e  clientes  dentro  do  ecossistema federado.

Além  dos  desafios  de  engenharia  de  software,  o  projeto  exige pesquisa  aplicada  em automação  de  workflows , segurança  de  APIs e engenharia  de  observabilidade ,  pois  o sistema  deverá  garantir  rastreabilidade  e  conformidade  em  tempo  real,  sem  comprometer  o desempenho operacional.

Em síntese, o AFO II (Automation of Federation Onboarding II) busca consolidar o estado da arte em automação de integração de aplicações federadas, ampliando o que foi desenvolvido no ciclo  anterior  e  transformando  um  processo  manual  e  suscetível  a  erros  em  um sistema autônomo, validado e auditável ,

## 2.4. Metodologia

Os  projetos conduzidos pela Universidade Federal do Ceará (UFC) em parceria com a Dell seguem  uma  metodologia  de  execução  padronizada,  aprimorada  ao  longo  de  anos  de cooperação. Essa metodologia integra práticas ágeis de desenvolvimento  distribuído a abordagens científicas de pesquisa aplicada, permitindo iterações curtas de entrega e revisão contínua do conhecimento produzido.

O  ciclo  do AFO  II inicia-se  com reuniões  de  levantamento  de  requisitos e análise  do processo  atual  de  onboarding ,  conduzidas  em  conjunto  com  a  equipe  de Authentication Identity  Management  (AIM) da  Dell.  Nessa  etapa,  são  mapeadas  as  dependências  entre módulos,  APIs  e  fluxos  de  aprovação,  bem  como  os  pontos  de  melhoria  para  o  processo automatizado. Os pesquisadores analisam ainda as implicações de segurança, conformidade e desempenho, identificando as áreas críticas que demandam automação.

Em  seguida,  inicia-se  a fase  de  concepção  e  planejamento  da  solução ,  que  envolve  a definição  da  arquitetura  do  sistema, a modelagem de microsserviços e o desenho das novas interfaces de usuário e painéis de observabilidade. O design segue princípios de usabilidade (UX) e adota os padrões do Dell Design System  (DDS) , garantindo consistência e acessibilidade.

A fase de desenvolvimento compreende a implementação dos módulos centrais previstos no escopo FY27 - incluindo o Automated Onboarding Module , o Request Module aprimorado, o OAuth Token Generation , e os módulos  de Observabilidade e Auditabilidade . O desenvolvimento  é  conduzido  de  forma  iterativa,  com  integração  contínua  ( CI/CD )  e  testes automatizados de regressão, segurança e conformidade.

Durante todo o projeto, são executadas atividades contínuas de documentação  e transferência  de  tecnologia  (TOT) . A cada  sprint, artefatos técnicos são  revisados  e repassados à Dell para validação e absorção do conhecimento. Nos meses finais, o foco recai sobre  a homologação  e  treinamento  da  equipe  Dell ,  com  sessões práticas de operação e manutenção da solução em ambiente produtivo.

O  acompanhamento  do  projeto  é  realizado  por  meio  de reuniões  de  revisão  periódicas , coordenadas  pelo  gerente  e  pelo  coordenador  científico,  assegurando  que  o  cronograma,  o orçamento e as metas técnicas sejam cumpridos.

Entre as principais características da metodologia destacam-se:

- Iterações  curtas  e  entregas  incrementais ,  permitindo  avaliar  resultados  e  ajustar  o curso do projeto rapidamente;
- Abordagem centrada em usuários e personas ,  garantindo  que as soluções atendam às reais necessidades dos administradores e equipes de integração;
- Integração  contínua  entre  pesquisa  e  engenharia ,  unindo  investigação  científica  e implementação prática;
- Participação  ativa  do  cliente  (PO  da  Dell) ,  com  feedback  constante  e  revisão  de funcionalidades em cada ciclo.

Essa  abordagem  tem  se  mostrado  eficiente  em  projetos  anteriores,  garantindo  agilidade, rastreabilidade e inovação contínua na entrega de soluções corporativas complexas.

## 2.5. Estrutura de Etapas com Cronograma e Atividades Planejadas

## Fase 1. Compreensão e Análise do Problema

## Etapa 1.1 Estudo do processo atual de Geração de Token OAuth

Nesta  fase,  serão  analisados  os  fluxos  atuais  de onboarding, mapeando as etapas manuais, dependências  entre  equipes  e  pontos  de  falha  nos  processos  de  submissão,  aprovação  e implantação.  A  equipe  também  estudará  as  oportunidades  de  automação  relacionadas  à geração de tokens OAuth, aos mecanismos de observabilidade e à integração com pipelines de CI/CD. Serão levantados os requisitos funcionais e não funcionais da solução, consolidando o entendimento técnico e operacional do problema.

Duração prevista: 03/2026 - 05/2026

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração de Sistemas, Pesquisador em Análise de Requisitos, Pesquisador em Observabilidade,  Especialista  em  Integração  de  Sistemas  ,  Gerente  de  Projeto,  Analista  de Requisitos.

## Etapa 1.2 Estudo das oportunidades de Observabilidade e Auditabilidade

Esta  etapa  tem  como  objetivo  analisar  o  processo  atual  de  implantação  de  aplicações  no ambiente federado e identificar oportunidades para incorporar mecanismos de observabilidade e auditabilidade que garantam maior transparência, rastreabilidade e confiabilidade às execuções automatizadas. O estudo permitirá mapear eventos críticos, fluxos de dados e pontos de coleta de  evidências,  bem  como  propor  diretrizes  iniciais  para  a  arquitetura  de  monitoramento  e auditoria  do  sistema.  Ao  final  do  período,  espera-se  obter  um  relatório  consolidado  das necessidades e possibilidades técnicas para implementação de um módulo de Observabilidade e Auditabilidade  que  fortaleça  a  governança,  a  segurança  e  a  conformidade  do  processo  de onboarding automatizado.

Duração prevista:

03/2026 - 05/2026

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Pesquisador  em  Análise de Requisitos, Consultor em Arquitetura de Software,  Especialista em  Testes  e  Devops  (Mestrando),  Pesquisador  em  Observabilidade, Especialista em Integração de Sistemas , Gerente de Projeto, Analista de Requisitos.

## Etapa 1.3 Mapeamento de oportunidades de DevOps

Esta etapa tem como objetivo analisar o fluxo atual de integração e implantação de aplicações no  ambiente  federado,  identificando  oportunidades  de  adoção  e  aprimoramento  de  práticas DevOps que promovam maior automação, eficiência e padronização no processo de onboarding do time Dell AIM. Serão estudados as interações entre equipes, os mecanismos existentes de integração contínua e  os  pontos  que  ainda  dependem  de  intervenção  manual  ou  que representam risco operacional. Especial atenção será dada à automação de testes dinâmicos, com  a  introdução  e  o  fortalecimento  do  uso  de  ferramentas  como Cypress ,  para  testes end-to-end  em  interfaces  web,  e Postman ,  para  validação  automatizada  de  APIs  REST.  A adoção dessas ferramentas visa reduzir falhas humanas, acelerar ciclos de validação e garantir maior cobertura de testes em  ambientes  de  homologação  e  produção.  A  partir  desse diagnóstico,  será  proposto  um  conjunto  de  melhorias  que  fortaleçam  a  entrega  contínua  e segura, aumentando a confiabilidade do ciclo de implantação e a escalabilidade da solução AFO II. Como resultado, espera-se obter uma visão estruturada das práticas DevOps recomendadas para o ambiente, indicando caminhos  para  evolução  gradual  e  aderentes  aos  padrões corporativos da Dell.

Duração prevista:

03/2026 - 05/2026

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Pesquisador  em  Análise de Requisitos, Consultor em Arquitetura de Software,  Especialista em  Testes  e  Devops  (Mestrando),  Pesquisador  em  Observabilidade, Especialista em Integração de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1, Designer 2, Analista de Requisitos (Mestrando), Desenvolvedor  Testes  e  DevOps  1,  Desenvolvedor  Testes  e/DevOps  2,  Gerente  de  Projeto, Analista de Requisitos, Desenvolvedor  Front-end  1,  Desenvolvedor  Back-End  DevOps 1,Desenvolvedor Back-End DevOps 2, Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior

## Etapa 1.3 Elicitação de Requisitos

Esta etapa consiste na elicitação e análise dos requisitos  funcionais  e  não  funcionais relacionados às novas funcionalidades previstas para o AFO II, incluindo o módulo de Geração de  Tokens  OAuth,  avanços  no  Módulo  de  Requisições, automação completa do processo de implantação e a incorporação dos módulos  de  Observabilidade  e  Auditabilidade.  Serão conduzidas  reuniões  com  stakeholders,  análise detalhada dos fluxos do ambiente federado e levantamento  de  necessidades  de  integração  com  os  sistemas  existentes  no  Federal  Auth Environment.  Também  serão  avaliados  aspectos  de  segurança,  conformidade  com  padrões como  NIST  800-171  e  CMMC,  usabilidade e aderência ao Dell Design System (DDS). Como resultado, será produzida a especificação consolidada de requisitos do projeto, servindo de base para  o  planejamento,  arquitetura  e  desenvolvimento  das  soluções  previstas  neste  ciclo  de extensão do AFO.

Duração prevista:

03/2026 - 05/2026

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Pesquisador  em  Análise de Requisitos, Consultor em Arquitetura de Software,  Especialista em  Testes  e  Devops  (Mestrando),  Pesquisador  em  Observabilidade, Especialista  em  Integração  de  Sistemas  ,  Analista  de  Requisitos  (Mestrando),  Gerente  de Projeto, Analista de Requisitos Analista de Testes.

## Fase 2  Planejamento e Projeto da Solução

## Etapa 2.1 Concepção da Interface de Usuário para Geração de Tokens OAuth

Com  base  no  diagnóstico  inicial,  esta  etapa  abrangerá  o  projeto  das  novas  interfaces  de Geração  de  Tokens  OAuth e Observabilidade/Auditabilidade, e o planejamento do pipeline de automação e implantação. Serão estabelecidas as diretrizes de segurança, os fluxos de dados e as tecnologias a serem utilizadas, alinhadas às boas práticas de desenvolvimento seguro. Os protótipos de interface serão criados com base nas diretrizes do Dell Design System, priorizando experiência do usuário e acessibilidade.

Duração prevista: 04/2026 - 07/2026

Participantes: Coordenador do Projeto,, Pesquisador em Análise de Requisitos,, Pesquisador em Observabilidade, , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End) Designer  1,  Designer  2,  Analista  de  Requisitos  ,  Gerente  de Projeto, Analista de Requisitos, Desenvolvedor Front-end 1 Analista de Testes, Desenvolvedor Front-End 2 Junior.

## Etapa 2.2 Projeto da Arquitetura de Geração de Tokens OAuth

Esta  etapa,  demandada  diretamente  pelo  cliente  como  prioridade  para  o  segundo  ciclo  do projeto,  tem  como objetivo definir a arquitetura do novo módulo de Geração de Tokens OAuth, componente essencial para ampliar a automação e garantir maior segurança e governança no processo  de  onboarding  de  aplicações.  A  arquitetura  proposta  deverá  especificar  de  forma detalhada  a  modelagem  das  entidades  envolvidas,  fluxos  de  autenticação,  integração com o sistema  de  requisições  e  demais  componentes  já  existentes  no  Federal  Auth  Environment, assegurando  aderência  às  políticas  corporativas  e  conformidade  com  normas  regulatórias relevantes. Além disso, serão avaliados requisitos de escalabilidade, disponibilidade e proteção de  credenciais,  garantindo  que  a  solução  seja  robusta,  segura  e  preparada  para  evoluções futuras.  Ao  final  desta  etapa,  a  equipe  entregará  a  especificação  arquitetural  completa,  que servirá como referência para o desenvolvimento, validação e implantação do módulo no AFO II.

Duração prevista:

04/2026 - 08/2026

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Pesquisador  em  Análise de Requisitos, Consultor em Arquitetura de Software, Especialista  em Testes e Devops , Pesquisador em Observabilidade, Especialista em Integração de Sistemas , Gerente de Projeto, Analista de Requisitos,  Desenvolvedor Front-end 1,  Desenvolvedor  Back-End  DevOps  1,Desenvolvedor  Back-End  DevOps  2,  Desenvolvedor Back-End DevOps 3, Desenvolvedor Front-End 2 Junior.

## Etapa 2.3 Projeto da Pipeline de CI/CD

Nesta etapa será projetada a pipeline de Integração Contínua e Entrega Contínua (CI/CD) que dará  suporte  à  automação  completa  do  processo  de implantação de aplicações no ambiente federado. Considerando que a automação de ponta a ponta é um dos objetivos centrais do AFO II, a definição dessa pipeline representa um passo crucial para assegurar que as transições entre desenvolvimento, homologação e produção ocorram de forma segura, padronizada e auditável. Serão  especificados  os  fluxos  de  build,  testes  automatizados,  validações  de  conformidade  e deploy  controlado  no  Oracle  Identity  and  Access  Management,  além  da  integração  com  o Módulo  de Solicitações e com os novos mecanismos de observabilidade previstos no projeto. Essa modelagem será realizada dentro do período planejado, permitindo que o desenvolvimento dos módulos na fase seguinte já seja conduzido de acordo com o pipeline definido. Ao final da etapa,  será  entregue  o  desenho  arquitetural  da  pipeline CI/CD, com diretrizes de segurança, padronização  e  governança  necessárias  para  suportar  a  operação  contínua  e  escalável  da solução AFO II.

Duração prevista:

04/2026 - 08/2026

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Consultor  em  Arquitetura  de  Software,  Especialista em  Testes  e Devops , Pesquisador em  Observabilidade, Especialista em  Integração  de  Sistemas  , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1, Designer 2, , Desenvolvedor Testes e DevOps 1, Desenvolvedor Testes e/DevOps 2, Gerente de  Projeto, Desenvolvedor  Front-end  1,  Desenvolvedor  Back-End  DevOps  1,Desenvolvedor Back-End DevOps 2, Desenvolvedor Back-End DevOps 3, Desenvolvedor Front-End 2 Junior

## Etapa 2.4 Concepção da Interface do Usuário de Observabilidade/Auditoria

Esta  etapa  será  dedicada  à  concepção  das  interfaces  de  usuário  responsáveis  por  fornecer visibilidade  às  execuções automatizadas do processo de onboarding federado, permitindo que administradores  e  equipes  operacionais  acompanhem  o  status  das  requisições, desempenho das automações e histórico de eventos auditáveis. O design das telas seguirá as diretrizes de experiência do usuário e acessibilidade do Dell Design System (DDS), garantindo consistência visual  com os módulos já implementados no AFO I e aderência às necessidades operacionais identificadas na fase de análise. Durante esta etapa, serão definidos os elementos de interação, visualização e filtragem de informações relevantes, além  de  protótipos  navegáveis  que permitirão validação preliminar com stakeholders. O trabalho será executado no período previsto em  cronograma,  permitindo  que  as  interfaces  estejam  prontas  para  implementação  na  fase seguinte. Como resultado, serão entregues os protótipos funcionais e a documentação de design das  telas,  fornecendo  uma  base  sólida  para  a  construção  dos  painéis  de  observabilidade  e auditoria do AFO II.

Duração prevista:

04/2026 - 07/2026

Participantes: Coordenador do Projeto,, Pesquisador em Integração de Sistemas, Pesquisador em  Análise  de  Requisitos,,  Pesquisador  em  Observabilidade,  Especialista  em  Integração  de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End) Designer 1, Designer 2, Analista de Requisitos (Mestrando), Gerente de Projeto, Analista de Requisitos.

## Etapa 2.5 Projeto da Arquitetura de Observabilidade/Auditoria

Esta  etapa  tem  como  finalidade  definir  a  arquitetura  técnica  que  sustentará  os  módulos  de Observabilidade e Auditabilidade do AFO  II, componentes  essenciais  para  assegurar  a rastreabilidade,  a  transparência  e  o  controle  das  execuções  automatizadas  no  ambiente federado. A arquitetura proposta deverá abranger a coleta, o processamento e o armazenamento estruturado de logs e eventos, além de estabelecer diretrizes para integração com  os  painéis  de  monitoramento  e  trilhas  de  auditoria  concebidos  na etapa anterior. Serão consideradas  as boas práticas de engenharia de observabilidade, segurança da informação e compliance, garantindo aderência aos padrões corporativos da Dell e às normas NIST 800-171 e CMMC.  Durante  o  período  previsto  para  esta  atividade, a equipe irá elaborar os modelos de dados, definir interfaces de integração entre serviços e projetar os mecanismos de correlação de eventos e alertas operacionais. Ao final, será entregue a especificação arquitetural detalhada do módulo, servindo como base para sua implementação na fase de desenvolvimento do AFO II.

Duração prevista:

04/2026 - 08/2026

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Consultor  em  Arquitetura  de  Software,  Especialista em  Testes  e Devops (Mestrando), Pesquisador em Observabilidade, Especialista em Integração de Sistemas, Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor  Junior 4 (Back-End),  Desenvolvedor  Junior  5  (Back-End),, Desenvolvedor  Testes  e  DevOps  1,  Desenvolvedor  Testes  e/DevOps  2,  Gerente  de Projeto,, Desenvolvedor  Front-end  1,  Desenvolvedor  Back-End  DevOps  1,Desenvolvedor  Back-End DevOps 2, Desenvolvedor Back-End DevOps 3, Desenvolvedor Front-End 2 Junior.

## Fase 3: Desenvolvimento de Soluções e Transferência de Tecnologia

## Etapa 3.1 - Desenvolvimento do Módulo de Integração Automatizada

Esta etapa compreende o desenvolvimento e integração dos principais componentes do sistema. Serão  aprimorados  os  módulos  de Automated  Onboarding e Request ,  implementando automação de ponta a ponta no fluxo de onboarding e adicionando validações automáticas de conformidade.  Estes módulos serão também integrados aos novos módulos de OAuth Token Generation ,  permitindo  o  gerenciamento  seguro  de  tokens  e  clientes,  e  os  módulos  de Observabilidade e Auditabilidade , que  fornecerão dashboards,  logs e indicadores de performance do processo de onboarding.

Duração prevista:

03/2026 - 08/2026

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Pesquisador  em  Análise de Requisitos, Consultor em Arquitetura de Software,  Especialista em  Testes  e  Devops  (Mestrando),  Pesquisador  em  Observabilidade, Especialista em Integração de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Analista de Requisitos (Mestrando), Desenvolvedor Testes e DevOps  1,  Desenvolvedor  Testes  e/DevOps  2,  Gerente  de  Projeto,  Analista  de  Requisitos, Desenvolvedor  Front-end  1,  Desenvolvedor  Back-End  DevOps  1,Desenvolvedor  Back-End DevOps 2, Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior.

## Etapa 3.2 - Desenvolvimento do Módulo de Solicitação

Nesta etapa serão desenvolvidas melhorias e expansões no Módulo de Solicitação responsável por  permitir  que  os  usuários  realizem  requisições  de  onboarding  de  aplicações  no  ambiente federado de forma estruturada, intuitiva e integrada aos demais componentes do AFO II. Esse módulo  contemplará  a  criação de uma interface aprimorada para submissão das informações necessárias  ao  processo  de  implantação,  além  de  um  dashboard  de  acompanhamento  que possibilitará  ao  solicitante  e  às  equipes  responsáveis  monitorar  o  progresso  da solicitação em tempo  real.  A  solução  deverá  incorporar  validações  automáticas de dados, assegurando que todas as informações estejam em conformidade com os requisitos operacionais e de segurança antes  do  início  da  automação.  Também  será  implementada a comunicação com os sistemas internos  do  Federal  Auth  Environment  e  com  os  demais  módulos  já  existentes  no  AFO  I, garantindo rastreabilidade e consistência na execução do fluxo. Ao final desta etapa, o Módulo de  Solicitação  estará  funcional  e  integrado  ao  ecossistema  da  automação,  viabilizando  uma experiência de onboarding mais eficiente, transparente e governável.

Duração prevista:

03/2026 - 05/2026

Participantes: Coordenador do Projeto, Pesquisador em Testes e DevOps, Pesquisador em Integração de Sistemas, Pesquisador em Análise de Requisitos, Consultor em Arquitetura de Software, Especialista  em Testes e Devops (Mestrando), Pesquisador em Observabilidade, Especialista em Integração de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1, Designer 2, Analista de Requisitos (Mestrando), Desenvolvedor Testes e DevOps 1, Desenvolvedor Testes e/DevOps 2, Gerente de Projeto, Analista de Requisitos,  Desenvolvedor Front-end 1, Desenvolvedor Back-End DevOps 1,Desenvolvedor Back-End DevOps 2, Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior

## Etapa 3.3 - Desenvolvimento do Módulo de Geração de Token OAuth

Esta  etapa  será  dedicada  ao  desenvolvimento  do  módulo  de  Geração  de  Tokens  OAuth, funcionalidade  estratégica  demandada  pelo  cliente e indispensável para garantir autenticação segura  e governável no processo de onboarding federado. As atividades aqui previstas serão conduzidas tomando como base os resultados da Etapa 1.1 - que analisou o processo atual de emissão e gestão de tokens no Federal Auth Environment - e da Etapa 2.2 - onde foi definida a arquitetura completa do módulo. Com isso, o desenvolvimento será orientado por requisitos operacionais reais e pela especificação arquitetural previamente aprovada. Serão implementadas APIs e interfaces para configuração de domínios, servidores e clientes, além de mecanismos  seguros  de  criação,  distribuição  e  armazenamento  de  tokens.  O  módulo  será integrado  ao Módulo de Solicitações, permitindo que a autenticação necessária às aplicações seja  provisionada  de  forma  automatizada,  consistente  e  auditável,  eliminando  dependências manuais no fluxo de implantação. Ao final desta etapa, o módulo estará funcional e apto para ser validado  nos  fluxos  de  automação  do  AFO  II,  contribuindo  diretamente  para  a  eficiência, segurança e escalabilidade do ambiente federado.

Duração prevista:

06/2026 - 01/2027

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Pesquisador  em  Análise de Requisitos, Consultor em Arquitetura de Software,  Especialista em  Testes  e  Devops  (Mestrando),  Pesquisador  em  Observabilidade, Especialista em Integração de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1, Designer 2, Analista de Requisitos (Mestrando), Desenvolvedor  Testes  e  DevOps  1,  Desenvolvedor  Testes  e/DevOps  2,  Gerente  de  Projeto, Analista de Requisitos, Desenvolvedor  Front-end  1,  Desenvolvedor  Back-End  DevOps 1,Desenvolvedor Back-End DevOps 2, Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior

## Etapa 3.4 - Implementação da Pipeline CD/CD

Nesta etapa será implementada a pipeline de Integração Contínua e Entrega Contínua (CI/CD), elemento essencial para viabilizar a automação completa do fluxo de implantação de aplicações no  ambiente  federado.  As  atividades  aqui  previstas  serão  conduzidas  com  base  no  projeto arquitetural elaborado na Etapa 2.3, garantindo que a implementação siga os fluxos, validações e  padrões  previamente  definidos.  A  pipeline  deverá  contemplar  automações de build, testes, verificações de conformidade e deploy controlado no Oracle Identity and Access Management, além da integração com o  Módulo  de  Solicitações  e  com  os  novos  mecanismos  de observabilidade e auditoria do AFO II. Também serão incorporados controles de rastreabilidade, proporcionando maior governança e segurança operacional. Ao término desta etapa, a pipeline estará configurada e pronta para suportar o desenvolvimento e entrega contínua dos módulos do AFO II, fortalecendo a eficiência e previsibilidade do processo de onboarding federado.

Duração prevista:

06/2026 - 01/2027

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração de Sistemas,Consultor em Arquitetura de Software, Especialista  em Testes e Devops (Mestrando),  Pesquisador  em  Observabilidade,  Especialista  em  Integração  de  Sistemas  , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1, Designer 2, , Desenvolvedor Testes e DevOps 1, Desenvolvedor Testes e/DevOps 2, Gerente de  Projeto, Desenvolvedor  Front-end  1,  Desenvolvedor  Back-End  DevOps  1,Desenvolvedor Back-End  DevOps  2,  Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior

## Etapa 3.5 - Implementação da Observabilidade/Auditoria

Esta etapa será dedicada à implementação dos mecanismos de observabilidade e auditabilidade definidos para o AFO II, assegurando visibilidade operacional e rastreabilidade das execuções automatizadas  no  processo  de  onboarding  federado.  O  desenvolvimento  será  realizado  com base nos resultados da Etapa 2.5 - que estabeleceu a arquitetura dessas capacidades - e nas necessidades identificadas na Etapa 1.2, garantindo que a solução reflita os requisitos técnicos e normativos levantados durante o estudo das oportunidades de monitoramento e auditoria. Serão configurados os pipelines de coleta e consolidação de logs e eventos, além de integrações com os painéis de acompanhamento concebidos para os usuários e equipes operacionais. Também serão implementados mecanismos de trilha de auditoria que permitam registrar ações críticas e decisões  automatizadas  do  sistema  de forma clara e segura, contribuindo para conformidade com padrões como NIST 800-171 e CMMC. Ao final da etapa, os módulos de observabilidade e auditabilidade  estarão  integrados  ao  ecossistema  do  AFO  II,  permitindo  o  acompanhamento contínuo da saúde do sistema, identificação rápida de falhas e comprovação de governança no ambiente federado.

Duração prevista:

06/2026 - 01/2027

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Consultor  em  Arquitetura  de  Software,  Especialista em  Testes  e Devops (Mestrando), Pesquisador em Observabilidade, Especialista em Integração de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1,  Designer 2, Desenvolvedor Testes e DevOps 1, Desenvolvedor Testes e/DevOps 2, Gerente de  Projeto,  Desenvolvedor  Front-end  1,  Desenvolvedor  Back-End  DevOps  1,Desenvolvedor Back-End  DevOps  2,  Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior

## Etapa 3.6 - Realização de Testes do Sistema

Nesta  fase  serão  realizados  testes  unitários,  de  integração,  segurança  e  desempenho  para validar todos os componentes. A solução passará por testes de homologação e implantação em ambiente produtivo, com monitoramento contínuo de logs e métricas.

Duração prevista:

03/2026 - 02/2027

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Pesquisador  em  Análise de Requisitos, Consultor em Arquitetura de Software,  Especialista em  Testes  e  Devops  (Mestrando),  Pesquisador  em  Observabilidade, Especialista em Integração de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1, Designer 2, Desenvolvedor Testes e DevOps 1, Desenvolvedor Testes e/DevOps 2, Gerente de Projeto, Desenvolvedor Front-end 1, Desenvolvedor Back-End DevOps  1,Desenvolvedor Back-End  DevOps  2,  Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior

## Etapa 3.7 - Preparação para Implantação em Produção

Nesta etapa ocorrerá o desenvolvimento e configuração da pipeline de implantação automatizada, garantindo uma transição segura e controlada da solução do ambiente de testes para  o  ambiente  de  produção.  O  processo  seguirá  os  requisitos  estabelecidos  para  uma implantação  estável,  incluindo  validações  técnicas  e  avaliações  de  conformidade  realizadas previamente. A equipe de desenvolvimento permanecerá disponível para apoiar e acompanhar a execução dessa implantação, conforme a equipe da Dell decidir avançar para o uso produtivo do sistema. Dessa forma, esta etapa assegurará que a solução AFO II esteja preparada para operar de forma contínua, confiável e aderente às normas corporativas do ambiente federado.

Duração prevista:

10/2026 - 02/2027

Participantes: Coordenador do Projeto, Pesquisador em Testes e DevOps, Pesquisador em Integração de Sistemas, Pesquisador em Análise de Requisitos, Consultor em Arquitetura de Software, Especialista  em Testes e Devops (Mestrando), Pesquisador em Observabilidade, Especialista em Integração de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1, Designer 2, Analista de Requisitos (Mestrando), Desenvolvedor Testes e DevOps 1, Desenvolvedor Testes e/DevOps 2, Gerente de Projeto, Analista de Requisitos,  Desenvolvedor Front-end 1, Desenvolvedor Back-End DevOps 1,Desenvolvedor Back-End DevOps 2, Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior

## Etapa 3.7 - Realização da Transferência de Tecnologia

A  transferência  de  tecnologia  ocorrerá  ao  longo de toda a execução do projeto, por meio de reuniões  periódicas  com  a  equipe  da  Dell,  nas  quais  o  conhecimento  será  continuamente compartilhado  e  discutido.  Toda  a  documentação técnica e de desenvolvimento será mantida atualizada,  de  modo  a  garantir  autonomia  total  da  Dell  na  operação  e  evolução  da  solução entregue.  Além  disso,  serão  produzidos  e  disponibilizados  manuais  do  usuário,  guias  de operação  e  demais  materiais  necessários  ao  correto  entendimento  do  fluxo  de  trabalho implementado, facilitando o uso e a manutenção do produto. Esses artefatos serão organizados e armazenados  no  Confluence,  garantindo  acesso  fácil  e  centralizado  para  as  equipes responsáveis,  reforçando  assim  os  objetivos  de  transferência  contínua  de  conhecimento  e sustentabilidade tecnológica do AFO II.

Duração prevista:

07/2026 - 02/2027

Participantes: Coordenador  do  Projeto,  Pesquisador  em  Testes  e  DevOps,  Pesquisador  em Integração  de  Sistemas,  Pesquisador  em  Análise de Requisitos, Consultor em Arquitetura de Software,  Especialista em  Testes  e  Devops  (Mestrando),  Pesquisador  em  Observabilidade,

Especialista em Integração de Sistemas , Desenvolvedor Junior 1 (Front-End), Desenvolvedor Junior 2 (Front-End), Desenvolvedor Junior 3 (Back-End), Desenvolvedor Junior 4 (Back-End), Desenvolvedor Junior 5 (Back-End), Designer 1, Designer 2, Analista de Requisitos (Mestrando), Desenvolvedor  Testes  e  DevOps  1,  Desenvolvedor  Testes  e/DevOps  2,  Gerente  de  Projeto, Analista de Requisitos, Desenvolvedor  Front-end  1,  Desenvolvedor  Back-End  DevOps 1,Desenvolvedor Back-End DevOps 2, Desenvolvedor Back-End DevOps 3, Analista de Testes, Desenvolvedor Front-End 2 Junior

## 2.6. Duração

Data de início:

01/03/2026

Data de estimada de término:

28/02/2027

## 2.7. Resultados Esperados

O  projeto AFO  II entregará  uma  versão  amadurecida  e pronta para produção da solução de automação de onboarding federado, com:

- Automação completa e contínua do processo de integração de aplicações;
- Validação automatizada de conformidade com normas de segurança e compliance;
- Integração dos módulos de Geração de Token OAuth , Observabilidade e Auditabilidade ;
- Painéis de auditoria e métricas operacionais;
- Documentação técnica e manual do usuário;
- Transferência tecnológica e treinamento para a equipe Dell;
- 1 software com inovação tecnológica derivada do projeto.

## 2.8. Indicadores de Resultados Esperados (§ 2º, art. 24, Decreto nº 5.906/2006)

| 1. Patentes depositadas no Brasil e no exterior Quantas patentes se espera gerar? Número de patentes                         | ☐   |
|------------------------------------------------------------------------------------------------------------------------------|-----|
| 2. Concessão de co-titularidade ou de participação nos resultados da pesquisa e desenvolvimento às instituições convenentes  | ☐   |
| 3. Protótipos, processos, softwares e produtos que incorporem inovação científica ou tecnológica Espera-se gerar 1 software. | x   |
| 4. Publicações científicas e tecnológicas em periódicos ou eventos científicos com revisão pelos pares.                      | ☐   |
| 5. Dissertações e teses defendidas.                                                                                          | ☐   |

## 3. Dos Recursos Necessários ao Desenvolvimento do Projeto

## 3.1 Introdução

Os recursos para o projeto ' Automation of Federation Onboarding Fase II ' foram estimados com base em metodologias diferentes dependendo de cada rubrica. Os recursos humanos direto e  indireto  foram  estimados  em  horas  mensais,  com  base  na  experiência  do coordenador da instituição e escopo do projeto. As demais rubricas foram estimadas por meio de cotações com fornecedores e a partir da larga experiência do coordenador e da equipe com gestão de projetos de pesquisa e desenvolvimento no contexto da Lei de Informática.

## 3.2 Recursos Humanos Diretos (Decreto nº 5.906/2006, art. 25, inciso III)

Função:

Coordenador do Projeto

Formação:

Superior com Doutorado

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Profissional  responsável  pela  coordenação científica  e  técnica  do  projeto,  realizando  a  orientação  científica  para  a  publicação  de artigos,  orientação  de  trabalhos  relacionadas  às  temáticas  deste  projeto,  definição de metodologia e instrumentos utilizados para a construção das tecnologias, realização de pesquisas,  revisão  bibliográfica,  e  acompanhamento  técnico  de  todos  os  artefatos gerados para a construção das tecnologias previstas.

Horas trabalhadas:

192 h

Total do dispêndio (remuneração total com encargos) : R$ 90.000,00

Função:

Pesquisador em Testes e DevOps

Formação:

Superior com Doutorado

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Profissional  responsável  pela  pesquisa  das melhores  práticas  para  planejamento  dos  cenários  e  casos  de  testes,  bem  como  os testes necessários para implantação da solução em produção na infraestrutura da Dell (PCF).  Sua  atuação  também  visa  garantir  o  correto  uso  das  melhores  práticas  para integração  contínua  e  entrega  contínua.  Além  disso,  também  fazem  parte  das  suas atividades: participação na elaboração do plano de testes, validação dos procedimentos e roteiros de testes, avaliação dos riscos e impactos dos testes, validação da configuração do ambiente necessário para realização dos testes automatizados e deploy em produção. Finalmente, será também  responsável  pela  pesquisa  das  melhores  práticas  para planejamento  dos  testes  de  desempenho,  visando  otimizar  serviços  e  melhorar  o desempenho na produção.

Horas trabalhadas:

192 h

Total do dispêndio (remuneração total com encargos) : R$ 66.000,00

Função:

Pesquisador em Integração de Sistemas

Formação:

Superior com Doutorado

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Responsável  pela  escolha  das estratégias e interfaces  necessárias  para  integração  de  componentes  na  aplicação,  bem  como  na definição de soluções para o projeto da arquitetura de modo a atender os requisitos de escalabilidade e otimização de desempenho. Suas atividades também envolvem estudar como  otimizar  as  consultas  do  banco  de  dados,  além  de  colaborar  no  design  e implementação  de  esquemas  de  dados  que  suportem  os  objetivos  da  pesquisa. Este profissional  atuará  como  consultor  científico,  em  constante conversa com a equipe de engenharia de software e outros líderes de pesquisa.

Horas trabalhadas:

192 h

Total do dispêndio (remuneração total com encargos) : R$ 66.000,00

Função:

Pesquisador em Análise de Requisitos

Formação:

Superior com Doutorado

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o projeto: Responsável pela condução das reuniões de compreensão do contexto técnico do projeto, bem como pelo levantamento de requisitos junto  ao  time  da  Dell  e  pela  criação,  manutenção e priorização do backlog de trabalho. Também será responsável pelo acompanhamento das cerimônias de gerenciamento do projeto (sprint planning, daily scrum, sprint, review e sprint retrospective) em parceria com o Gerente de Projetos e o Analista de Requisitos.

Horas trabalhadas

: 192 h

Total do dispêndio (remuneração total com encargos): R$ 66.000,00

Função

: Consultor em Arquitetura de Software

Formação

: Superior com Doutorado

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto :  Responsável  pelas  atividades  de  auxílio  de análise de viabilidade, seleção de tecnologias, desenho e especificação da arquitetura da solução.

Horas trabalhadas:

192 h

Total do dispêndio (remuneração total com encargos): R$ 48.000,00

Função:

Especialista em Testes e Devops

Formação:

Superior com Mestrando, Mestrado ou Doutorando

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional que atuará nos estudos relacionados à condução dos testes da solução proposta, bem como em práticas DevOps a  serem  utilizadas  no  contexto  do  projeto.  Sua  atuação  será  em  parceria  com  o Pesquisador em Testes e DevOps.

Horas trabalhadas:

960 h

Total do dispêndio (remuneração total com encargos): R$ 27.000,00

Função:

Pesquisador em Observabilidade

Formação:

Superior com Mestrado, Doutorando ou Doutor

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa para  o projeto: Responsável  por  definir  e  implementar estratégias de observabilidade que permitam o monitoramento abrangente do desempenho,  disponibilidade  e  comportamento  dos  sistemas  desenvolvidos.  Suas atividades incluem a escolha e configuração de ferramentas de instrumentação, coleta e análise de métricas, logs e traces, bem como a definição de indicadores de desempenho que auxiliem na detecção de anomalias e na identificação de anti padrões arquiteturais. Este profissional também atuará na proposição de melhorias contínuas para a arquitetura e os processos de monitoramento, garantindo que as soluções adotadas atendam aos requisitos  de  escalabilidade  e  confiabilidade.  Além  disso,  exercerá  papel  de consultor científico, colaborando com a equipe de engenharia de software e demais pesquisadores na interpretação dos dados observados e na definição de estratégias para otimização dos sistemas.

Horas trabalhadas:

192 h

Total do dispêndio (remuneração total com encargos) :

Função:

Especialista em Integração de Sistemas

Formação:

Superior com Mestrado, Doutorando

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Pesquisador que atuará nos estudos relacionados à integração da solução a ser desenvolvida, especialmente em relação às estratégias  de  comunicação  dos microsserviços. Atuará na definição da arquitetura da solução, seus componentes e interfaces, além do desenvolvimento das integrações com novos  front-ends, serviços que  provêm  estratégias para validação  e  implantação automatizada  das  aplicações.  Sua  atuação  será  em  parceria  com  o  Pesquisador  em Integração de Sistemas.

Horas trabalhadas:

960 h

Total do dispêndio

(remuneração total com encargos) : R$ 38.400,00

Função:

Desenvolvedor Junior 1 (Front-End)

Formação: Médio

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional responsável pela implementação de correções,  melhorias  e  novas  funcionalidades  relacionadas  em  aplicações front-end , especialmente na Interface do Usuário para Coleta de Dados e Aprovação de Aplicações. Deve também implementar testes unitários e auxiliar os testadores nas devolutivas dos testes  para  que  se  possa  fazer o teste novamente no menor tempo possível, visando produzir uma plataforma segura e estável. Também suporta na execução de ajustes finais na solução possibilitando a transferência tecnológica para a Dell.

Horas trabalhadas:

1.200 h

Total do dispêndio (remuneração total com encargos) : R$ 16.800,00

Função:

Desenvolvedor Junior 2 (Front-End)

Formação: Médio

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional responsável pela implementação de correções,  melhorias  e  novas  funcionalidades  relacionadas  em  aplicações front-end , especialmente na Interface do Usuário para Coleta de Dados e Aprovação de Aplicações. Deve também implementar testes unitários e auxiliar os testadores nas devolutivas dos testes  para  que  se  possa  fazer o teste novamente no menor tempo possível, visando produzir uma plataforma segura e estável. Também suporta na execução de ajustes finais na solução possibilitando a transferência tecnológica para a Dell.

Horas trabalhadas:

1.200 h

Total do dispêndio (remuneração total com encargos) : R$ 16.800,00

Função:

Desenvolvedor Junior 3 (Back-End)

Formação: Médio

Data de Início:

01/03/2026

R$ 66.000,00

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional responsável pela implementação de correções, melhorias  e  novas  funcionalidades  relacionadas  nos  serviços back-end referentes aos microsserviços de transferência e validação do processo de onboarding, bem  como  o  processo  automatizado  de  implantação  de  aplicações.  Deve  também implementar testes unitários e auxiliar os testadores nas devolutivas dos testes para que se  possa  fazer  o  teste  novamente  no  menor  tempo  possível,  visando  produzir  uma plataforma segura e estável. Também suporta na execução de ajustes finais na solução possibilitando a transferência tecnológica para a Dell.

Horas trabalhadas:

1.200 h

Total do dispêndio

(remuneração total com encargos) : R$ 16.800,00

Função:

Desenvolvedor Junior 4 (Back-End)

Formação: Médio

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional responsável pela implementação de correções, melhorias  e  novas  funcionalidades  relacionadas  nos  serviços back-end referentes aos microsserviços de transferência e validação do processo de onboarding, bem  como  o  processo  automatizado  de  implantação  de  aplicações.  Deve  também implementar testes unitários e auxiliar os testadores nas devolutivas dos testes para que se  possa  fazer  o  teste  novamente  no  menor  tempo  possível,  visando  produzir  uma plataforma segura e estável. Também suporta na execução de ajustes finais na solução possibilitando a transferência tecnológica para a Dell.

Horas trabalhadas:

1.200 h

Total do dispêndio (remuneração total com encargos) : R$ 16.800,00

Função:

Desenvolvedor Junior 5 (Back-End)

Formação: Médio

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional responsável pela implementação de correções, melhorias  e  novas  funcionalidades  relacionadas  nos  serviços back-end referentes aos microsserviços de transferência e validação do processo de onboarding, bem  como  o  processo  automatizado  de  implantação  de  aplicações.  Deve  também implementar testes unitários e auxiliar os testadores nas devolutivas dos testes para que se  possa  fazer  o  teste  novamente  no  menor  tempo  possível,  visando  produzir  uma plataforma segura e estável. Também suporta na execução de ajustes finais na solução possibilitando a transferência tecnológica para a Dell.

Horas trabalhadas:

1.200 h

Total do dispêndio (remuneração total com encargos) : R$ 16.800,00

Função:

Analista de Requisitos Junior

Formação:

Superior Mestrando

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Profissional  responsável  pela  realização das especificações funcionais para o desenvolvimento da tecnologia prevista no escopo deste projeto,  participando  das  atividades  de  levantamento  de  requisitos  das  novas  telas  e funcionalidades, além dos requisitos que guiarão as pesquisas sobre as estratégias de validação e onboarding automático das aplicações. Além disso, atuará diretamente com o Coordenador do Projeto, Gerente de Projetos e apoio ao trabalho do Product Owner e Analista de Requisitos/Scrum.

Horas trabalhadas:

960 h

Total do dispêndio (remuneração total com encargos) : R$ 27.000,00

Função:

Designer Junior 1

Formação: Médio

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Responsável pelas atividades relacionadas a planejamento, prototipação, implementação de interfaces e experiência de usuário da da solução  proposta,  em  especial  da  Interface  do  Usuário  para  Coleta  de  Dados  e Aprovação  de  Aplicações.  Através  do  uso  das  boas  práticas  e  conceitos  de  User Experience (UX) e IHC, auxiliará na elicitação de requisitos e prototipação da interface que  auxiliará  a  equipe  de  engenharia de software no desenvolvimento do front-end do projeto.  Também  fará  benchmarks  de  soluções  existentes  e  conduzirá  reuniões  de prototipação e entrevistas com os usuários.

Horas trabalhadas:

1.200 h

Total do dispêndio

(remuneração total com encargos) : R$ 16.800,00

Função:

Designer Junior 2

Formação: Médio

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Responsável pelas atividades relacionadas a planejamento, prototipação, implementação de interfaces e experiência de usuário da da solução  proposta,  em  especial  da  Interface  do  Usuário  para  Coleta  de  Dados  e Aprovação  de  Aplicações.  Através  do  uso  das  boas  práticas  e  conceitos  de  User Experience (UX) e IHC, auxiliará na elicitação de requisitos e prototipação da interface que  auxiliará  a  equipe  de  engenharia de software no desenvolvimento do front-end do projeto.  Também  fará  benchmarks  de  soluções  existentes  e  conduzirá  reuniões  de prototipação e entrevistas com os usuários.

Horas trabalhadas:

1.200 h

Total do dispêndio

(remuneração total com encargos) : R$ 16.800,00

Função:

Desenvolvedor Junior Testes e DevOps 1

Formação: Médio

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional responsável pela implementação e realização dos testes, avaliação dos riscos e impactos dos testes da solução proposta. Em  conjunto  com  os  resultados dos  testes  realizados,  seu  papel  também  inclui acompanhar  os  relatórios  gerados  pelas  ferramentas  de  análise  de  código,  como Sonarqube,  Snyk  e  JFrog  Xray,  a  fim  de  evoluir  a  solução  desenvolvida  e  torná-la compatível com as necessidades do público-alvo, além de possibilitar a identificação de possíveis falhas e trechos de código que  podem  ser  aprimorados  (Garantia  de Qualidade). Finalmente, este profissional será responsável pela manutenção da pipeline do  projeto,  garantindo  que  ela  esteja  sempre  disponível  e  em  conformidade  com  as recomendações da Dell.

Horas trabalhadas:

1.000 h

Total do dispêndio

(remuneração total com encargos) : R$ 16.800,00

Função:

Desenvolvedor Junior Testes e DevOps 2

Formação: Médio

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional responsável pela implementação e realização dos testes, avaliação dos riscos e impactos dos testes da solução proposta. Em  conjunto  com  os  resultados dos  testes  realizados,  seu  papel  também  inclui acompanhar  os  relatórios  gerados  pelas  ferramentas  de  análise  de  código,  como Sonarqube,  Snyk  e  JFrog  Xray,  a  fim  de  evoluir  a  solução  desenvolvida  e  torná-la compatível com as necessidades do público-alvo, além de possibilitar a identificação de possíveis falhas e trechos de código que  podem  ser  aprimorados  (Garantia  de Qualidade). Finalmente, este profissional será responsável pela manutenção da pipeline do projeto, garantindo que ela esteja sempre disponível e conforme as recomendações da Dell.

Horas trabalhadas:

1.000 h

Total do dispêndio (remuneração total com encargos) : R$ 16.800,00

Função:

Gerente de Projetos

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Profissional  responsável  pela  realização das atividades  de  gerenciamento  do  escopo  (documentação  do  escopo  e  controle  de mudanças do projeto), cronograma (planejamento das atividades e atualização de status com  o  time  do  projeto),  custos  (mapeamento  de  custos  necessários  para  suportar  a realização das atividades da equipe), aquisições (mapeamento das aquisições necessárias para realização do escopo), recursos humanos  (gerenciamento  das atividades da equipe do projeto), dentre outras áreas, para que os resultados previstos neste projeto fossem alcançados no tempo, na qualidade e no orçamento previstos para este projeto.

Horas trabalhadas:

672 h

Total do dispêndio (remuneração total com encargos) : R$ 116.743,69

Função:

Analista de Requisitos

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Profissional  responsável  pela  realização das especificações funcionais para o desenvolvimento da tecnologia prevista no escopo deste projeto,  participando  das  atividades  de  levantamento  de  requisitos  das  novas  telas  e funcionalidades, além dos requisitos que guiarão as pesquisas sobre as estratégias de validação e onboarding automático das aplicações. Além disso, atuará nas entrevistas, condução  de  reuniões  para  planejamento,  revisão  e apresentação dos resultados das Sprints .  Além  disso,  atuará  diretamente  com  o  Coordenador  do  Projeto e Gerente de Projetos para acompanhar o cronograma e preparar o planejamento das entregas.

Horas trabalhadas:

1.920 h

Total do dispêndio (remuneração total com encargos) : R$ 130.322,68

Função:

Desenvolvedor Front-end 1

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Responsável por desenvolver as aplicações e as técnicas  de front-end que  foram  definidas  pelos  pesquisadores  e  especialistas,  em especial  na  Interface  do  Usuário  para  Coleta  de  Dados  e  Aprovação  de  Aplicações. Também  deve  implementar  os  testes  unitários  e  de  integração,  além  de  auxiliar  os testadores  nas  devolutivas  dos  testes  para  que  se possa fazer o teste novamente no menor  tempo  possível,  visando  produzir  uma  plataforma  segura  e  estável.  Atua  no desenvolvimento da solução, implementando as novas interfaces da solução, bem como realizando  as  integrações  com  os  serviços  do back-end, APIs  de  terceiros  e  demais sistemas. Também é responsável pela documentação do projeto e suporta a execução de ajustes finais na solução para que seja possível a transferência tecnológica do mesmo para a Dell.

Horas trabalhadas:

1.920 h

Total do dispêndio (remuneração total com encargos) :

R$ 112.600,14

Função:

Desenvolvedor Front-end 2 Junior

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Responsável por desenvolver as aplicações e as técnicas  de  front-end  que  foram  definidas  pelos  pesquisadores  e  especialistas,  em especial  na  Interface  do  Usuário  para  Coleta  de  Dados  e  Aprovação  de  Aplicações. Também deve implementar os testes unitários e de integração com o back-end, além de auxiliar os testadores nas devolutivas dos testes para que se possa testar novamente no menor  tempo  possível,  visando  produzir  uma  plataforma  segura  e estável. Também é responsável  pela  documentação  do  projeto  e  suporta a execução de ajustes finais na solução para que seja possível a transferência tecnológica do mesmo para a Dell.

Horas trabalhadas:

1.920 h

Total do dispêndio (remuneração total com encargos) :

Função:

Desenvolvedor Back-end/DevOps 1

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Responsável por desenvolver os serviços de back-end para as soluções que foram definidas pelos pesquisadores e especialistas do projeto.  Sua  atuação  deve  se  concentrar  na  implementação  dos  microsserviços  de transferência e componentes necessários para o processo de implantação automatizado das aplicações. Deve implementar testes unitários e auxiliar os testadores nas devolutivas  dos  testes  para  que  se  possa  fazer  o  teste  novamente  no  menor  tempo possível,  visando  produzir  uma  plataforma segura e estável. Atua no desenvolvimento das soluções e nas APIs de integração com demais componentes do sistema. Também é responsável pela documentação do back-end do projeto e suporta a execução de ajustes finais  na  solução  para  que  seja  possível  a  transferência  tecnológica  do  mesmo  para  a Dell.

Horas trabalhadas:

1.920 h

Total do dispêndio (remuneração total com encargos) : R$ 111.610,56

Função:

Desenvolvedor Back-end/DevOps 2

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Responsável por desenvolver os serviços de back-end para as soluções que foram definidas pelos pesquisadores e especialistas do projeto.  Sua  atuação  deve  se  concentrar  na  implementação  dos  microsserviços  de transferência e componentes necessários para o processo de implantação automatizado das aplicações. Deve implementar testes unitários e auxiliar os testadores nas devolutivas  dos  testes  para  que  se  possa  fazer  o  teste  novamente  no  menor  tempo possível,  visando  produzir  uma  plataforma segura e estável. Atua no desenvolvimento das soluções e nas APIs de integração com demais componentes do sistema. Também é responsável pela documentação do back-end do projeto e suporte a execução de ajustes finais  na  solução  para  que  seja  possível  a  transferência  tecnológica  do  mesmo  para  a Dell.

Horas trabalhadas:

1.920 h

Total do dispêndio (remuneração total com encargos) : R$ 120.004,70

Função:

Desenvolvedor Back-end/DevOps 3

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação  e  justificativa  para  o  projeto: Responsável por desenvolver os serviços de back-end para as soluções que foram definidas pelos pesquisadores e especialistas do projeto.  Sua  atuação  deve  se  concentrar  na  implementação  dos  microsserviços  de transferência e componentes necessários para o processo de implantação automatizado das aplicações. Deve implementar testes unitários e auxiliar os testadores nas devolutivas  dos  testes  para  que  se  possa  fazer  o  teste  novamente  no  menor  tempo possível,  visando  produzir  uma  plataforma segura e estável. Atua no desenvolvimento das soluções e nas APIs de integração com demais componentes do sistema. Também é responsável pela documentação do back-end do projeto e suporte a execução de ajustes finais  na  solução  para  que  seja  possível  a  transferência  tecnológica  do  mesmo  para  a Dell.

Horas trabalhadas:

1.920 h

Total do dispêndio (remuneração total com encargos) : R$ 104.701,97

Função:

Analista de Testes

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Profissional responsável pelos planejamento dos cenários e Casos de Testes, elaboração do plano de testes, elaboração e implementação dos procedimentos e roteiros de testes, configuração do ambiente necessário, implementação  e  realização  dos  testes  e  avaliação  dos  riscos e impactos dos testes. Este profissional também deverá acompanhar os relatórios gerados pelas ferramentas de análise  de  código,  como  Sonarqube,  Snyk  e  JFrog  Xray,  a  fim  de  evoluir  a  solução desenvolvida  e  torná-la  compatível  com  as  necessidades  do  público-alvo,  além  de possibilitar  a  identificação  de  possíveis  falhas  e  trechos  de  código  que  podem  ser aprimorados  (Garantia  de  Qualidade).  Seu  papel  também  inclui  o  alinhamento  dos resultados de cada ciclo de teste em conjunto com a equipe.

Horas trabalhadas:

1.920 h

Total do dispêndio (remuneração total com encargos) : R$ 118.355,26

## 3.3 Recursos Humanos Indiretos (Decreto nº 5.906/2006, art. 25, inciso IV)

Função:

Analista de Suporte TI

Formação:

Superior

Data de Início:

01/03/2026

Data de Fim:

28/02/2027

Atuação e justificativa para o projeto: Responsável pelo gerenciamento da infraestrutura  de  rede,  manutenção  e  monitoramento  dos  recursos  computacionais (Desktops,  Notebooks,  Servidores,  Switchs,  Roteadores,  Access  Points,  No  Breaks, Impressoras).  Suporte  técnico  aos  usuários  da  equipe,  além  de  outras  atribuições administrativas.

Horas trabalhadas:

1.920 h

Total do dispêndio (remuneração total com encargos) : R$ 114.956,10

## 3.4 Viagens (Decreto nº 5.906/2006, art. 25, inciso VII)

Não se aplica

## 3.5 Serviços Técnicos (Decreto n.º 5.906/2006, art. 25, inciso IX)

Não se aplica

## 3.6 Equipamentos e Software (Decreto n.º 5.906/2006, art. 25, inciso I)

Dispêndio  (Adequação):

07  Notebooks  Dell  G15 - Quantitativo  adequado  para

atender as atividades da equipe do projeto.

Tipo de Apropriação

: Equipamento TICs - Aquisição

Tipo de Apropriação

: Equipamento TICs - Aquisição

Descrição: Notebook Dell G15 - Notebook Máquina dedicada à equipe do projeto para realização das atividades de desenvolvimento e teste dos algoritmos e funcionalidades que serão desenvolvidas durante a execução deste projeto, com configurações iguais ou semelhantes: Microcomputador Portátil Dell G15 5530 (Core I7-13650HX, GeForce RTX 4050, RAM 32 GB, SSD 1 TB, Wi-fi, FHD, Bat. 6 Cel.,

Game Pass, McAfee(R) 30day Trial, Win 11 Pro POR)

Valor:

R$ 49.000,00

Justificativa (Pertinência): Máquinas dedicadas à equipe do projeto para realização das atividades de pesquisa e desenvolvimento inerentes ao escopo do projeto.

Dispêndio (Adequação): 3  unidades-chave de acesso HSK -  Quantitativo adequado em relação os novos perfis do projeto

Tipo de Apropriação

: Equipamento Outros - Aquisição

Descrição:

Equipamento utilizado para a autenticação ao acesso à rede Dell

Valor:

R$ 600,00

Justificativa (Pertinência):

Chaves físicas de acesso à infraestrutura da rede Dell.

Dispêndio (Adequação): 3 unidades licenças Google Workspace Business Standard Quantitativo adequado em relação os novos perfis do projeto

Tipo de Apropriação

: Software - Licença anual

Descrição: Cessão de direito ao uso de licenças Google, necessária para acesso do às ferramentas corporativas.

Valor:

R$ 2.700,00

Justificativa  (Pertinência): Cessão  de  direito  ao  uso  de  licenças  G-suíte  basic  do Google,  necessária  para  acesso  do  às  ferramentas  corporativas  como:  Gmail,  Drive, Agendas, Pacote Office na Nuvem, entre outras, como suporte às atividades realizadas em todas as etapas deste projeto. Será utilizada para serviços em nuvem da Google para que  todos  os colaboradores do projeto tenham melhor desempenho na realização das atividades,  bem  como  suporte à realização de diversas atividades técnicas do projeto, tais  como a construção online e colaborativa de documentos, relatórios online utilizados na realização dos testes e das atividades de pesquisa, além de viabilizar um processo que preconiza maior segurança à proteção dos dados, considerando que as contas de e-mail  utilizadas  para  comunicação  entre  os  membros  do  projeto  e  o  cliente,  são gerenciadas por um usuário administrador.

## 3.7 Treinamento (Decreto nº 5.906/2006, art. 25, inciso VIII)

Não se aplica

- 3.8 Livros / Periódicos Técnicos (Decreto nº 5.906/2006, art. 25, inciso V)

Não se aplica

- 3.9 Material de Consumo (Decreto nº 5.906/2006, art. 25, inciso VI)

Não se aplica

- 3.10 Obra Civil / Construções (Decreto de nº 5.906, de 26 de setembro de 2006, art. 25º, inciso Il)

Não se aplica

## 3.11 Outros Correlatos (Decreto nº 5.906/2006, art. 25, inciso X)

## 3.12 Custos Incorridos pela instituição

Discriminação  dos  principais  dispêndios  e  destinações: Despesas  operacionais incorridas pela instituição tais como despesas decorrentes das atividades administrativas e financeiras realizadas para suporte ao Projeto.

## Valor: R$ 415.953,04

Justificativa: São  considerados  como  custos  incorridos  os valores descritos a seguir, conforme previsto no decreto nº 6.405, de 19 de março de 2008, respeitando o limite de até 20% do montante a ser gasto no projeto: os valores com constituição de reserva a ser aplicada em  pesquisa, desenvolvimento  e  inovação  do setor de tecnologias da informação e comunicação, pela UFC, de acordo com o Art. 25, § 5o., Decreto 5906/2006 que  somam (R$  88.533,63) ; os valores referentes aos  custos  incorridos  para  o desenvolvimento do projeto, que incluem os custos de 10% do valor total do projeto (R$ 171.423,18) ,  relativos  ao  interveniente  financeiro FASTEF, conforme prerrogativa da Lei no  8.958,  de  1994,  Decreto  8.240/14,  Lei  no  10.973/04,  Lei  13.243/16  e  Decreto 9.283/18; bem como os valores referentes aos custos incorridos para o desenvolvimento do projeto na UFC conforme resolução 14/2022 - CONSUNI, que totalizam dos custos do projeto (R$  85.711,59)  calculados  pela  CPO/PROPLAD/UFC,  os  quais  deverão  ser debitados no Código 28955-8 (Outros Ressarcimentos), na Fonte 250 e serão realizados conforme  os  repasses  que  a empresa fará, e a FASTEF se obriga a transferi-lo até o último dia útil do mês seguinte ao da arrecadação de cada parcela. Estes valores estão previstos como cumprimento das obrigações de acordo com o que determina a legislação vigente incluindo, mas não se limitando às Leis no. 8.248/91, no. 10.176/2001 e Lei  no. 11.077/04 e ao Decreto 5.906/2006. E ainda (R$ 70.284,64) , necessárias para possibilitar a realização das atividades do projeto, tais como: seguro de vida dos bolsistas, tarifas bancárias,  ASO,  material  de  limpeza  de  ambiente,  manutenção  de  equipamentos  e laboratórios,  correios,  sistemas  de  assinatura  em  plataforma  digital,  licenças  Google, entre outras despesas.

## 3.13. Quadros Resumo dos Recursos Necessários ao Desenvolvimento do Projeto

|                            | RH Direto       | RH Direto   | RH Indireto   | RH Indireto   | Total           |
|----------------------------|-----------------|-------------|---------------|---------------|-----------------|
| Nível                      | Superior        | Médio       | Superior      | Médio         |                 |
| Quantidade de pessoas      | 17              | 9           | 1             |               | 27              |
| Valor (R$)                 | R$ 1.395.775,68 | R$ 151.200  | R$ 114.956,10 |               | R$ 1.661.931,78 |
| Total de horas trabalhadas | 18.144          | 10.800      | 1.920         |               | 30.864          |

| Rubrica                              | Total           | %       |
|--------------------------------------|-----------------|---------|
| RH Total                             | R$ 1.661.931,78 | 78,02%  |
| Obras Civis                          |                 |         |
| Serviços Técnicos                    |                 |         |
| Livros e Periódicos Técnicos         |                 |         |
| Outros Correlatos                    |                 |         |
| Equipamento e Software               | R$ 52.300,00    | 2,46%   |
| Material De Consumo                  |                 |         |
| Treinamento                          |                 |         |
| Viagens                              |                 |         |
| Custo Incorrido (+ Fundo de Reserva) | R$ 415.953,03   | 19,53%  |
| TOTAL DE DISPÊNDIOS                  | R$ 2.130.184,82 | 100,00% |

## 3.14. Cronograma Previsto dos Gastos

<!-- image -->

<!-- image -->

4. Das Disposições Gerais

O  presente  Plano  de  Trabalho  é  parte  integrante  do xxº  ACORDO  DE  COOPERAÇÃO TÉCNICA E CIENTÍFICA celebrado entre DELL, UFC e ASTEF .

A assinatura de testemunhas fica dispensada por força do que prevê o Art. 784, § 4º da Lei  nº  13.105/2015,  ficando  estabelecido  que:  (i)  será  válida  e  plenamente  eficaz  qualquer modalidade de assinatura eletrônica prevista em lei e; (ii) a data de assinatura desse documento será a data em que a última assinatura eletrônica ocorrer.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

## UNIVERSIDADE FEDERAL DO CEARÁ CNPJ: 07.272.636/0001-31 PROF. CUSTÓDIO LUIS SILVA ALMEIDA Reitor CPF: 078.883.173-91

## CONVENIADA

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

## A FUNDAÇÃO ASTEF - FUNDAÇÃO DE APOIO A SERVIÇOS TÉCNICOS, ENSINO E FOMENTO A PESQUISAS Joaquim Perúcio Pessoa Filho

## CNPJ: 08.918.421/0001-08 Diretor Presidente CPF: 404.268.903-53

## INTERVENIENTE

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

## DELL COMPUTADORES DO BRASIL LTDA EMPRESA

Nome: Mauricio Helfer

CPF:

915.855.700-87
