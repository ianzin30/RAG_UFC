# SAAR.pdf

Exclusivo  para  Lei  da  Informática   
PROJETO  DE  PESQUISA  E  DESENVOLVIMENTO  Plano  de  Trabalho  
Projeto  
Storage  Analytics  and  Auto-Reclamation  II  
Coordenador  na  Instituição  
Lincoln  Souza  Rocha  
 
Empresa  
Instituição  
Universidade  Federal  do  Ceará  -  UFC  Fundação  de  Apoio  a  Serviços  Técnicos,  Ensino  e  Fomento  a  Pesquisas  -  ASTEF  
Versão:  1.0  
Outubro/2025

1.  Classificação  do  Projeto   
1.1.  Tipo  do  Projeto   Hardware   ☐  
Hardware  com  software  embarcado   ☐  
Melhoria  de  Processo  Produtivo   ☐  
Software   x  
Software  Aplicativo   ☐  
Formação  e  Capacitação  Profissional   ☐  
Outro   ☐   Especificação:  aplicável  apenas  se  outros  tipos   
1.2.  Área  de  Aplicação  do  Projeto   
J.62  -  Atividades  dos  serviços  de  tecnologia  da  informação   
1.3.  Enquadramento  das  Atividades  do  Projeto  conforme  art.  2º,  Decreto  nº  
10.356/2020,
 
alterado
 
pelo
 
Decreto
 
nº
 
10.602/2021
 
  I  -  pesquisa  básica  -  pesquisa  experimental  ou  teórica  executada  primariamente  para  a  aquisição  de  conhecimento  novo  sobre  os  fundamentos  subjacentes  aos  fenômenos  e  fatos  observáveis,  sem  qualquer  aplicação  particular  ou  uso  em  vista;  
X  
II  –  pesquisa  aplicada  -  pesquisa  original  realizada  para  adquirir  conhecimento  e  que  se  dirige  primariamente  a  um  objetivo  ou  a  um  alvo  prático  específico;  
 III  –  desenvolvimento  experimental  -  trabalho  sistemático,  baseado  em  conhecimento  preexistente  e  destinado  à  produção  de  novos  produtos  e  processos  ou  ao  aperfeiçoamento  dos  produtos  e  processos  existentes;  
 IV  -  inovação  tecnológica  -  a  implementação  de  produto,  quer  seja  ele  bem  ou  serviço,  ou  processo  tecnológico  novo,  ou  significativamente  aprimorado,  nos  termos  do  disposto  no  inciso  IV  do  caput  do  art.  2º  da  Lei  nº  10.973,  de  2  de  dezembro  de  2004;

2.  Descrição  do  Projeto  de  Pesquisa  e  Desenvolvimento  
2.1.
 
Introdução
 
 
O  crescimento  exponencial  do  volume  de  dados  armazenados  e  o  uso  desigual  dos  recursos  
entre
 
usuários
 
representam
 
um
 
dos
 
principais
 
desafios
 
da
 
administração
 
moderna
 
de
 
infraestrutura
 
de
 
TI.
 
Essa
 
realidade
 
impacta
 
diretamente
 
os
 
times
 
de
 
Storage
 
Management
 
da
 
Dell,
 
que
 
enfrentam
 
cenários
 
de
 
subutilização
 
e
 
sobrecarga
 
de
 
armazenamento,
 
baixa
 
previsibilidade
 
de
 
consumo
 
e
 
ausência
 
de
 
uma
 
visão
 
consolidada
 
sobre
 
a
 
infraestrutura
 
global.
  Atualmente,  ferramentas  como  o  CIS  Dashboard  reúnem  métricas  de  consumo  e  permitem  a  
visualização
 
de
 
endpoints
 
individuais
 
de
 
diferentes
 
produtos
 
de
 
armazenamento.
 
No
 
entanto,
 
o
 
sistema
 
ainda
 
carece
 
de
 
funcionalidades
 
de
 
análise
 
preditiva
,
 
dashboards
 
agrupáveis
 
e
 
integração
 
analítica
 
entre
 
produtos
,
 
o
 
que
 
limita
 
a
 
visão
 
sistêmica
 
e
 
dificulta
 
a
 
previsão
 
de
 
saturações
 
e
 
anomalias
 
no
 
uso
 
dos
 
endpoints.
  Com  base  nesse  contexto,  foi  concebido  o  projeto  Storage  Analytics  and  Auto-Reclamation  
(SAAR)
 
—
 
uma
 
plataforma
 
desenvolvida
 
para
 
automatizar
 
a
 
análise
 
e
 
a
 
recuperação
 
de
 
espaço
 
de
 
armazenamento
,
 
oferecendo
 
visões
 
analíticas
 
abrangentes
 
sobre
 
padrões
 
de
 
uso,
 
tendências
 
de
 
crescimento
 
e
 
aderência
 
às
 
políticas
 
de
 
retenção.
 
O
 
SAAR
 
representa
 
uma
 
mudança
 
de
 
paradigma:
 
substitui
 
operações
 
reativas,
 
baseadas
 
em
 
solicitações
 
pontuais
 
de
 
limpeza,
 
por
 
processos
 
proativos
 
e
 
orientados
 
por
 
dados
,
 
apoiados
 
por
 
inteligência
 
analítica
 
e
 
automação
 
de
 
políticas.
  Durante  o  primeiro  ciclo,  ocorrido  durante  o  ano  de  2025  (Ano  Fiscal  de  2026),  foi  entregue  o  
MVP
 
da
 
solução,
 
com
 
integração
 
inicial
 
a
 
alguns
 
produtos
 
de
 
armazenamento
 
(notadamente
 
ECS
),
 
coleta
 
de
 
dados
 
do
 
sistema
 
CIS
 
Dashboard
,
 
e
 
mecanismos
 
analíticos
 
de
 
previsão
 
e
 
recomendação
 
de
 
ações
 
de
 
auto-reclamação
 
de
 
espaço
 
em
 
endpoints.
 
O
 
sistema
 
identifica
 
pontos
 
de
 
superutilização
 
e
 
subutilização,
 
prevê
 
saturações
 
e
 
apoia
 
decisões
 
baseadas
 
em
 
políticas
 
corporativas
 
de
 
uso
 
de
 
capacidade.
  Entretanto,  desafios  importantes  emergiram,  como  a  dificuldade  de  acesso  a  instâncias  
simuladas
 
de
 
produtos
 
de
 
armazenamento,
 
a
 
necessidade
 
de
 
integração
 
unificada
 
entre
 
múltiplas
 
plataformas
 
e
 
a
 
definição
 
de
 
processos
 
padronizados
 
de
 
auto-reclamação
 
(redimensionamento
 
e
 
recuperação
 
de
 
espaço
 
alocado).
 
Esses
 
desafios
 
são
 
o
 
ponto
 
de
 
partida
 
para
 
o
 
ciclo
 
2026
 
(Ano
 
Fiscal
 
de
 
2027),
 
que
 
visa
 
consolidar
 
o
 
SAAR
 
como
 
uma
 
solução
 
de
 
produção,
 
expandindo
 
a
 
integração
 
a
 
novos
 
produtos,
 
amadurecendo
 
seus
 
módulos
 
de
 
análise
 
e
 
automação
 
e
 
introduzindo
 
novos
 
mecanismos
 
de
 
observabilidade
 
e
 
governança.

2.2.  Objetivo  e  Escopo   
Objetivo  Geral  
O  objetivo  deste  projeto  é  aprimorar  e  expandir  a  plataforma  SAAR  (Storage  Analytics  and  
Auto-Reclamation)
,
 
consolidando-a
 
como
 
uma
 
ferramenta
 
de
 
governança
 
inteligente
 
para
 
análise,
 
previsão
 
e
 
automação
 
da
 
utilização
 
de
 
armazenamento
 
corporativo.
 
O
 
sistema
 
buscará
 
oferecer
 
integração
 
completa
 
com
 
diferentes
 
produtos
 
Dell,
 
permitir
 
análises
 
avançadas
 
e
 
fornecer
 
painéis
 
de
 
observabilidade
 
que
 
consolidam
 
logs,
 
estatísticas
 
e
 
ações
 
executadas.
 
Escopo  e  Estrutura  de  Trabalho  
O  escopo  do  projeto  FY27  está  dividido  em  tarefas  de  melhorias  e  de  novas  funcionalidades,  
que
 
visam
 
evoluir
 
a
 
solução
 
a
 
um
 
nível
 
de
 
maturidade
 
de
 
produção.
 
A.  Melhorias   
Estas  atividades  têm  como  foco  o  aperfeiçoamento  dos  módulos  já  desenvolvidos ,  a  
conclusão
 
das
 
integrações
 
planejadas
 
e
 
o
 
refinamento
 
do
 
processo
 
de
 
auto-reclamação.
 
1.  Extensão  da  Integração  com  Novos  Produtos:  O  módulo  ETL  do  SAAR  será  
expandido
 
para
 
integrar-se
 
a
 
uma
 
gama
 
mais
 
ampla
 
de
 
produtos
 
de
 
armazenamento
 
da
 
Dell,
 
incluindo
 
Unity
,
 
PowerScale
 
(Isilon)
,
 
PowerFlex
 
e
 
outros.
 
Essa
 
integração
 
permitirá
 
a
 
coleta,
 
padronização
 
e
 
análise
 
de
 
metadados
 
de
 
uso
 
em
 
escala
 
corporativa.
 
2.  Ampliação  das  Análises  e  Identificação  de  Padrões:  As  análises  de  uso  e  predição  
de
 
capacidade
 
serão
 
estendidas
 
para
 
incorporar
 
novas
 
dimensões
 
—
 
aplicações,
 
classes
 
de
 
usuários
 
e
 
casos
 
de
 
uso
 
—
 
ampliando
 
a
 
capacidade
 
do
 
SAAR
 
de
 
identificar
 
padrões
 
de
 
consumo,
 
prever
 
gargalos
 
e
 
propor
 
recomendações
 
com
 
base
 
em
 
diferentes
 
perfis
 
de
 
uso.
 
3.  Conclusão  e  Estruturação  do  Processo  de  Auto-Reclamação:  Será  definido  e  
implementado
 
um
 
processo
 
completo
 
de
 
auto-reclamação,
 
considerando
 
as
 
particularidades
 
de
 
cada
 
pilar
 
de
 
armazenamento
 
(
Storage
 
Pillar
).
 
Os
 
pilares
 
são
 
subdivisões
 
do
 
Dell
 
Storage
 
Team
 
focadas
 
em
 
famílias
 
de
 
produtos
 
de
 
armazenamento
 
(
blocks
,
 
files
 
e
 
objects
).
 
As
 
regras
 
e
 
ações
 
de
 
gerenciamento
 
serão
 
executadas
 
diretamente
 
dentro
 
dos
 
produtos
 
Dell,
 
suportadas
 
por
 
algoritmos
 
de
 
predição
 
e
 
detecção
 
de
 
anomalias.
 
4.  DevOps  e  Suporte  à  Produção:  Implementação  de  suporte  integral  a  deploys  
automatizados
 
e
 
alinhamento
 
com
 
práticas
 
de
 
CI/CD
,
 
garantindo
 
escalabilidade,
 
reprodutibilidade
 
e
 
operação
 
sem
 
intervenção
 
manual.
 
O
 
objetivo
 
é
 
permitir
 
o
 
trânsito
 
contínuo
 
do
 
ambiente
 
de
 
testes
 
para
 
produção,
 
com
 
governança
 
automatizada.
 
B.  Novas  Funcionalidades  
Este  conjunto  de  atividades  visa  introduzir  novos  recursos  de  observabilidade,  métricas  e  
monitoramento
 
que
 
complementam
 
a
 
análise
 
e
 
a
 
automação
 
do
 
SAAR:
 
1.  Mecanismos  de  Observabilidade:  Desenvolvimento  de  funcionalidades  para  registro  
detalhado
 
das
 
ações
 
executadas
 
na
 
plataforma
 
tais
 
como
 
atualizações
 
de
 
regras,
 
aprovações,
 
modificações
 
e
 
operações
 
automatizadas.
 
2.  Métricas  e  Estatísticas  de  Processamento:  Implementação  de  coleta  e  visualização  
de
 
métricas
 
sobre
 
o
 
funcionamento
 
interno
 
do
 
SAAR
 
(quantidade
 
de
 
regras
 
disparadas,
 
volume
 
de
 
espaço
 
recuperado,
 
tempo
 
médio
 
de
 
execução
 
de
 
tarefas
 
etc.).
 
3.  Dashboard  de  Observabilidade:  Entrega  de  um  painel  consolidado  que  reúna  logs  e

estatísticas  dos  diferentes  componentes  do  SAAR,  fornecendo  transparência  e  auditoria  
sobre
 
o
 
ciclo
 
completo
 
de
 
análise
 
e
 
recuperação.
 
 
2.3.  Problemática  Científico-Tecnológica    O  crescimento  contínuo  dos  volumes  de  dados  armazenados  nas  infraestruturas  corporativas  da  
Dell
 
impõe
 
desafios
 
cada
 
vez
 
mais
 
complexos
 
para
 
a
 
gestão
 
eficiente
 
de
 
recursos
 
de
 
armazenamento
.
 
Com
 
centenas
 
de
 
sistemas
 
e
 
produtos
 
distintos
 
—
 
como
 
ECS,
 
Unity,
 
PowerScale
 
(Isilon)
 
e
 
PowerFlex
 
—
 
coexistindo
 
em
 
um
 
ecossistema
 
heterogêneo,
 
a
 
ausência
 
de
 
um
 
controle
 
unificado
 
de
 
consumo,
 
previsibilidade
 
e
 
automação
 
tem
 
levado
 
à
 
subutilização
 
de
 
recursos
,
 
retenção
 
indevida
 
de
 
dados
 
e
 
aumento
 
dos
 
custos
 
operacionais
.
  A  gestão  atual  de  capacidade  ainda  depende  de  procedimentos  reativos:  o  espaço  é  liberado  
apenas
 
quando
 
há
 
solicitações
 
manuais
 
ou
 
situações
 
críticas.
 
Essa
 
abordagem
 
fragmentada
 
limita
 
a
 
eficiência
 
e
 
impede
 
a
 
adoção
 
de
 
políticas
 
preventivas
 
de
 
auto-reclamação
 
e
 
otimização
 
inteligente
 
de
 
uso
 
de
 
espaço
.
 
Além
 
disso,
 
a
 
ausência
 
de
 
visibilidade
 
consolidada
 
entre
 
produtos
 
dificulta
 
a
 
detecção
 
precoce
 
de
 
anomalias
 
e
 
a
 
aplicação
 
de
 
políticas
 
corporativas
 
de
 
retenção
 
de
 
dados.
  A  problemática  científica  e  tecnológica  do  projeto  SAAR  II  reside  justamente  na  automação  
inteligente
 
de
 
governança
 
de
 
armazenamento
,
 
aliando
 
análise
 
preditiva
,
 
integração
 
de
 
múltiplas
 
plataformas
 
e
 
execução
 
automatizada
 
de
 
políticas
 
de
 
recuperação
 
de
 
espaço
.
 
O
 
desafio
 
central
 
é
 
desenvolver
 
uma
 
arquitetura
 
escalável
 
de
 
ETL
 
(Extract,
 
Transform,
 
Load)
 
capaz
 
de
 
integrar,
 
padronizar
 
e
 
processar
 
dados
 
oriundos
 
de
 
produtos
 
com
 
diferentes
 
APIs,
 
formatos
 
e
 
granularidades,
 
construindo
 
uma
 
visão
 
consolidada
 
e
 
consistente
 
sobre
 
o
 
uso
 
de
 
capacidade.
  Do  ponto  de  vista  analítico,  há  uma  demanda  por  mecanismos  de  previsão  de  saturação  e  
detecção
 
de
 
padrões
 
de
 
uso
 
anômalos
,
 
utilizando
 
modelagem
 
estatística
 
e
 
técnicas
 
de
 
machine
 
learning.
 
Esses
 
mecanismos
 
devem
 
alimentar
 
módulos
 
de
 
decisão
 
e
 
permitir
 
a
 
execução
 
automatizada
 
de
 
ações
 
de
 
auto-reclamação,
 
respeitando
 
regras
 
de
 
negócio,
 
níveis
 
de
 
acesso
 
e
 
requisitos
 
de
 
segurança.
  Outro  desafio  científico  está  na  automação  dos  processos  de  limpeza  e  reconfiguração ,  que  
devem
 
ocorrer
 
de
 
forma
 
coordenada
 
entre
 
sistemas
 
heterogêneos,
 
com
 
validação
 
de
 
segurança,
 
logs
 
e
 
rollback.
 
Isso
 
requer
 
a
 
criação
 
de
 
um
 
mecanismo
 
orquestrador
 
que
 
combine
 
as
 
regras
 
de
 
análise
 
com
 
as
 
APIs
 
de
 
execução,
 
implementando
 
fluxos
 
automáticos
 
de
 
exclusão,
 
redimensionamento
 
e
 
realocação
 
de
 
dados.
  Além  da  automação,  o  projeto  busca  consolidar  mecanismos  avançados  de  observabilidade  e  
auditoria
,
 
que
 
permitam
 
visualizar
 
a
 
origem
 
das
 
ações,
 
seus
 
resultados
 
e
 
os
 
ganhos
 
de
 
capacidade
 
obtidos.
 
Essa
 
rastreabilidade
 
é
 
essencial
 
para
 
assegurar
 
transparência,
 
confiabilidade
 
e
 
conformidade
 
regulatória
,
 
especialmente
 
em
 
ambientes
 
de
 
missão
 
crítica.
  Portanto,  a  problemática  do  SAAR  II  envolve  a  integração  de  três  dimensões  de  PD&I:  ●  pesquisa  aplicada  em  análise  de  dados  e  automação  inteligente,  ●  engenharia  de  software  para  integração  de  sistemas  corporativos  complexos,  e

●  desenvolvimento  experimental  de  pipelines  orquestrados  de  decisão  e  execução,  com  
rastreabilidade
 
completa.
 ●   Essa  combinação  caracteriza  o  projeto  como  uma  atividade  de  Pesquisa  Aplicada  e  
Desenvolvimento
 
Experimental
,
 
conforme
 
o
 
art.
 
2º
 
do
 
Decreto
 
nº
 
10.356/2020.
  2.4.  Metodologia    Os  projetos  de  PD&I  conduzidos  pelo  Departamento  de  Computação  da  Universidade  
Federal
 
do
 
Ceará
 
(UFC)
 
nas
 
instalações
 
do
 
Laboratório
 
Alan
 
Turing
 
(ATLab)
 
em
 
parceria
 
com
 
a
 
Dell
 
seguem
 
uma
 
metodologia
 
padronizada,
 
testada
 
e
 
aprimorada
 
em
 
anos
 
de
 
colaboração
 
contínua.
 
Essa
 
metodologia
 
combina
 
práticas
 
de
 
métodos
 
ágeis
,
 
adequadas
 
para
 
equipes
 
de
 
desenvolvimento
 
distribuídas,
 
com
 
a
 
abordagem
 
científica
 
de
 
pesquisa
 
aplicada,
 
permitindo
 
que
 
investigação
 
e
 
engenharia
 
evoluam
 
de
 
forma
 
integrada
 
e
 
iterativa.
  O  projeto  inicia-se  com  reuniões  de  levantamento  e  validação  de  requisitos ,  nas  quais  as  
equipes
 
da
 
UFC
 
e
 
da
 
Dell
 
discutem
 
as
 
necessidades
 
específicas
 
dos
 
módulos
 
de
 
automação
 
e
 
análise
 
de
 
armazenamento.
 
Essa
 
etapa
 
é
 
fundamental
 
para
 
compreender
 
a
 
arquitetura
 
atual
 
dos
 
produtos
 
de
 
storage,
 
os
 
fluxos
 
de
 
dados
 
existentes
 
e
 
as
 
necessidades
 
de
 
integração
 
entre
 
as
 
APIs
 
dos
 
diferentes
 
sistemas
 
Dell
 
(ECS,
 
Unity,
 
PowerScale
 
(Isilon),
 
PowerFlex,
 
entre
 
outros).
  A  partir  desse  entendimento,  os  pesquisadores  realizam  estudos  de  domínio  técnico  e  
concepção
 
da
 
arquitetura
 
da
 
solução
,
 
investigando
 
protocolos
 
de
 
integração,
 
formatos
 
de
 
metadados
 
e
 
padrões
 
de
 
políticas
 
corporativas
 
de
 
retenção
 
e
 
exclusão.
 
Nessa
 
fase,
 
são
 
definidos
 
os
 
componentes
 
centrais
 
do
 
sistema
 
—
 
o
 
processo
 
ETL
,
 
o
 
módulo
 
de
 
analytics
,
 
o
 
motor
 
de
 
auto-reclamação
 
e
 
o
 
dashboard
 
de
 
observabilidade
 
—,
 
bem
 
como
 
suas
 
relações
 
e
 
responsabilidades
 
dentro
 
do
 
ecossistema
 
de
 
automação.
  Em  paralelo  à  pesquisa  aplicada,  a  equipe  de  engenharia  de  software  dá  início  à  implementação  
dos
 
módulos,
 
com
 
foco
 
inicial
 
na
 
maturação
 
do
 
pipeline
 
ETL
 
e
 
nas
 
integrações
 
com
 
novos
 
produtos
 
de
 
armazenamento
.
 
O
 
desenvolvimento
 
segue
 
um
 
processo
 
iterativo,
 
com
 
revisões
 
frequentes,
 
integração
 
contínua
 
(
CI/CD
)
 
e
 
aplicação
 
de
 
testes
 
automatizados
 
de
 
regressão,
 
segurança
 
e
 
desempenho.
 
São
 
conduzidos
 
testes
 
unitários,
 
de
 
integração
 
e
 
funcionais
,
 
com
 
uso
 
de
 
ferramentas
 
de
 
análise
 
de
 
código
 
para
 
medir
 
cobertura
 
e
 
qualidade.
  A  metodologia  contempla  também  atividades  contínuas  de  documentação  e  transferência  
tecnológica
 
(TOT)
.
 
A
 
cada
 
ciclo
 
de
 
desenvolvimento,
 
os
 
artefatos
 
técnicos
 
são
 
atualizados
 
e
 
validados
 
junto
 
à
 
equipe
 
Dell,
 
permitindo
 
a
 
absorção
 
gradual
 
do
 
conhecimento.
 
Nos
 
meses
 
finais,
 
são
 
realizadas
 
sessões
 
de
 
treinamento
 
e
 
homologação
 
da
 
solução,
 
consolidando
 
a
 
transferência
 
de
 
tecnologia
 
e
 
a
 
implantação
 
em
 
ambiente
 
produtivo.
 
O
 
acompanhamento
 
e
 
controle
 
do
 
projeto
 
são
 
realizados
 
pelo
 
coordenador
 
e
 
pelo
 
gerente
 
de
 
projeto,
 
garantindo
 
o
 
cumprimento
 
do
 
cronograma,
 
a
 
execução
 
dentro
 
do
 
orçamento
 
e
 
a
 
entrega
 
de
 
resultados
 
com
 
valor
 
técnico
 
e
 
aplicabilidade
 
prática.
  Entre  as  principais  características  da  metodologia  adotada,  destacam-se:  ●  Ciclos  curtos  de  desenvolvimento  e  entrega  incremental ,  favorecendo  a  validação  
contínua
 
das
 
funcionalidades
 
junto
 
à
 
Dell;
 ●  Coleta  de  requisitos  orientada  por  personas  e  histórias  de  usuário ,  assegurando  
clareza
 
no
 
entendimento
 
das
 
demandas
 
e
 
melhor
 
comunicação
 
entre
 
as
 
equipes;

●  Integração  contínua  entre  pesquisa  e  engenharia ,  em  que  a  investigação  científica  
retroalimenta
 
o
 
desenvolvimento
 
de
 
software;
 ●  Participação  ativa  do  cliente  (PO) ,  com  reuniões  de  acompanhamento,  revisões  de  
sprint
 
e
 
validações
 
de
 
entregas,
 
garantindo
 
que
 
o
 
projeto
 
mantenha
 
aderência
 
aos
 
objetivos
 
de
 
negócio.
  Essa  metodologia  tem  se  mostrado  eficiente  na  condução  de  projetos  complexos  de  automação  
e
 
análise
 
corporativa,
 
equilibrando
 
a
 
geração
 
de
 
conhecimento
 
técnico
 
com
 
a
 
entrega
 
de
 
soluções
 
prontas
 
para
 
uso
 
produtivo.
 
2.5.  Estrutura  de  Etapas  com  Cronograma  e  Atividades  Planejadas     Fase  1:  Análise  e  Entendimento  do  Problema    Etapa  1.1  Análise  de  Dados  Esta  etapa  se  estende  por  todo  o  projeto  e  será  dedicada  aos  estudos  do  ecossistema  de  
armazenamento
 
da
 
Dell
 
e
 
à
 
identificação
 
das
 
oportunidades
 
de
 
melhoria
 
em
 
relação
 
ao
 
gerenciamento
 
de
 
capacidade
 
e
 
processos
 
de
 
auto-reclamação.
 
Serão
 
mapeadas
 
as
 
APIs,
 
os
 
fluxos
 
de
 
dados
 
e
 
as
 
métricas
 
disponíveis
 
nos
 
sistemas
 
ECS,
 
Unity,
 
PowerScale
 
(Isilon)
 
e
 
PowerFlex.
 
O
 
objetivo
 
é
 
compreender
 
o
 
formato,
 
frequência
 
e
 
confiabilidade
 
dos
 
dados
 
coletados
 
e
 
documentar
 
as
 
lacunas
 
existentes.
 
Também
 
serão
 
realizadas
 
a
 
análise
 
do
 
pipeline
 
atual
 
de
 
ETL
 
e
 
a
 
definição
 
dos
 
requisitos
 
para
 
sua
 
expansão,
 
contemplando
 
as
 
novas
 
fontes
 
de
 
dados
 
e
 
produtos
 
de
 
armazenamento.
 
Duração
 
prevista:
 
03/2026
 
–
 
02/2027
 Participantes:  Coordenador  de  Projetos,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Ciência
 
de
 
Dados
 
,
 
Pesquisador
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Especialista
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Especialista
 
em
 
Banco
 
de
 
Dados
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos
  Etapa  1.2  -  Definição  da  arquitetura  final  (processo  ETL  e  implantação  SAAR)  Nesta  etapa,  será  atualizada  uma  arquitetura  final   baseada  em  microsserviços,  componentes  
em
 
camadas
 
e
 
processamento
 
orientado
 
a
 
eventos.
 
Esta
 
etapa
 
envolverá
 
a
 
seleção
 
de
 
tecnologias
 
(linguagens,
 
frameworks,
 
ferramentas),
 
especificação
 
de
 
esquemas
 
de
 
banco
 
de
 
dados,
 
design
 
de
 
APIs
 
de
 
backend,
 
protótipos
 
de
 
frontend,
 
métodos
 
de
 
análise
 
de
 
armazenamento
 
e
 
procedimentos
 
de
 
recuperação.
 
O
 
desenvolvimento
 
seguirá
 
um
 
modelo
 iterativo  e  incremental.   Duração  prevista:  03/2026  –  04/2026  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,
 
Especialista
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Especialista
 
em
 
Banco
 
de
 
Dados
 
,
 
Especialista
 
em
 
Visualização
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Designer
 
de
 
UI/UX,
 
Desenvolvedor
 
Full-stack
 
1,
 
Desenvolvedor
 
Full-stack
 
2.
   Etapa  1.3  -  Mapeamento  de  Integrações  com  Produtos  de  Armazenamento  A  Dell  possui  diversos  produtos  de  armazenamento,  cada  um  com  suas  próprias  APIs  de  acesso  
a
 
dados
 
e
 
acesso
 
a
 
funções
 
de
 
auto-reclamação.
 
Nesta
 
etapa,
 
serão
 
definidos
 
os
 
produtos-alvo

neste  ciclo  do  projeto,  através  de  levantamento  de  prioridades  junto  aos  stakeholders  de  cada  
pilar
 
de
 
armazenamento.
 
Na
 
sequência,
 
será
 
mapeada
 
como
 
se
 
dará
 
a
 
integração
 
da
 
solução
 
SAAR
 
com
 
os
 
produtos
 
de
 
armazenamento
 
priorizados
 
para
 
o
 
projeto.
 
Cada
 
produto
 
pode
 
ser
 
disponibilizado
 
em
 
múltiplas
 
versões,
 
e
 
diferenças
 
entre
 
versões
 
das
 
APIs
 
precisam
 
ser
 
mapeadas.
 
O
 
resultado
 
dessa
 
atividade
 
irá
 
alimentar
 
o
 
desenho
 
da
 
arquitetura
 
de
 
ETL
 
e
 
do
 
módulo
 
de
 
Auto-reclamação.
  Duração  prevista:  03/2026  –  04/2026  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,
 
Especialista
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Especialista
 
em
 
Banco
 
de
 
Dados
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Full-stack
 
1,
 
Desenvolvedor
 
Full-stack
 
2.
   Etapa  1.3  -  Levantamento  de  Requisitos  Nesta  etapa,  serão  conduzidas  atividades  de  elicitação  de  requisitos,  incluindo  análise  de  
documentação
 
e
 
entrevistas
 
com
 
usuários
 
e
 
stakeholders.
 
Será
 
elaborado
 
um
 
documento
 
de
 
visão
 
do
 
produto
 
para
 
estabelecer
 
e
 
comunicar
 
os
 
objetivos
 
de
 
longo
 
prazo
 
do
 
sistema
 
de
 
gerenciamento
 
de
 
armazenamento.
 
Além
 
disso,
 
será
 
especificado
 
um
 
conjunto
 
inicial
 
de
 
requisitos
 
para
 
definir
 
o
 
escopo
 
do
 
desenvolvimento.
  Duração  prevista:  03/2026  –  06/2026  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  Designer  
de
 
UI/UX
 
Trainee
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Designer
 
de
 
UI/UX,
 
Desenvolvedor
 
Full-stack
  
1,
 
Desenvolvedor
 
Full-stack
 
2.
  Fase  2:  Planejamento  e  Desenho  da  Solução   Etapa  2.1  -  Análise  de  Visualização  Com  base  no  diagnóstico  técnico,  esta  etapa  se  estende  por  todo  o  projeto  e  envolverá  os  
estudos
 
de
 
soluções
 
de
 
visualizações
 
para
 
atendimento
 
aos
 
requisitos
 
do
 
sistema.
 
Esses
 
estudos
 
compreendem
 
análise
 
dos
 
dados,
 
concepção
 
de
 
protótipos,
 
validação
 
de
 
concepções
 
e
 
suporte
 
ao
 
time
 
de
 
desenvolvimento
 
para
 
integração
 
das
 
visualizações
 
na
 
UI
 
do
 
sistema.
 
Em
 
especial,
 
os
 
requisitos
 
relacionados
 
aos
 
módulos
 
de
 
analytics,
 
à
 
auto-reclamação
 
e
 
aos
 
mecanismos
 
de
 
observabilidade
 
são
 
os
 
mais
 
críticos
 
no
 
aspecto
 
de
 
planejamento
 
das
 
visualizações.
 Duração  prevista:  03/2026  –  02/2027  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Ciência  de  Dados  ,  Pesquisador  em  
Engenharia
 
de
 
Dados,
 
Pesquisador
 
em
 
Visualização
 
,
 
Especialista
 
em
 
Visualização,
 
UI/UX
 
Designer
 
Jr
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Designer
 
de
 
UI/UX.
  Etapa  2.2  -  Concepção  de  Ul/UX  Essa  etapa  é  para  a  elaboração  de  protótipos  de  alta  fidelidade  a  partir  dos  requisitos  do  projeto  
e
 
dos
 
estudos
 
de
 
visualização,
 
a
 
fim
 
de
 
aperfeiçoar
 
funcionalidades
 
existentes
 
e/ou
 
desenvolver
 
novas.
 
O
 
processo
 
respeita
 
boas
 
práticas
 
de
 
usabilidade
 
e
 
experiência
 
do
 
usuário,
 
em
 
conformidade
 
com
 
os
 
padrões
 
da
 
Dell.
 
Também
 
serão
 
definidos
 
os
 
fluxos
 
de
 
integração
 
entre
 
as
 
interfaces
 
de
 
usuário
 
dos
 
módulos,
 
assegurando
 
usabilidade
 
e
 
clareza
 
das
 
informações
 
apresentadas.
 Duração  prevista:  03/2026  –  06/2026

Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Visualização  ,  Especialista  em  
Visualização
 
,
 
UI/UX
 
Designer
 
Jr.
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Designer
 
de
 
UI/UX
  Etapa  2.3  -  ETL  e  Design  Detalhado  da  Arquitetura  da  Solução  Esta  etapa  envolverá  o  projeto  detalhado  da  arquitetura  do  SAAR  II.  Neste  ciclo  do  projeto,  as  
adições
 
mais
 
significativas
 
são
 
o
 
pipeline
 
ETL,
 
o
 
módulo
 
de
 
auto-reclamação
 
e
 
as
 
novas
 
funcionalidades.
 
A
 
definição
 
do
 
protocolo
 
de
 
execução
 
da
 
pipeline
 
ETL
 
levará
 
em
 
conta
 
a
 
frequência
 
de
 
execução
 
das
 
coletas
 
de
 
dados,
 
bem
 
como
 
o
 
impacto
 
da
 
sua
 
execução
 
nos
 
respectivos
 
serviços
 
de
 
armazenamento.
 
Uma
 
vez
 
definido
 
o
 
protocolo
 
de
 
execução
 
que
 
o
 
ETL
 
seguirá,
 
ele
 
será
 
incorporado
 
ao
 
desenho
 
geral
 
da
 
arquitetura,
 
acomodando
 
eventuais
 
mudanças
 
no
 
mesmo.
 
O
 
módulo
 
de
 
auto-reclamação
 
será
 
desenhado
 
para
 
atender
 
o
 
mapeamento
 
produzido
 
na
 
etapa
 
1.3.
 
Por
 
fim,
 
os
 
requisitos
 
associados
 
às
 
novas
 
funcionalidades
 
serão
 
considerados
 
no
 
desenho
 
da
 
arquitetura.
 Duração  prevista:  04/2026  –  05/2026  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,
 
Especialista
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Especialista
 
em
 
Banco
 
de
 
Dados
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Full-stack
  
1,
 
Desenvolvedor
 
Full-stack
 
2.
  Etapa  2.4  -  Definição  do  Processo  de  Auto-Reclamação  Essa  etapa  será  dedicada  ao  estudo,  definição,  projeto  e  implantação  do  processo  de  
Auto-Reclamação.
 
A
 
partir
 
das
 
análises
 
de
 
dados
 
definidas
 
na
 
etapa
 
1.1,
 
um
 
conjunto
 
de
 
regras,
 
análises
 
e
 
modelos
 
de
 
previsão
 
(forecasting)
 
será
 
definido
 
para
 
que
 
o
 
SAAR
 
detecte
 
com
 
precisão
 
o
 
estado
 
atual
 
e
 
os
 
possíveis
 
estados
 
futuros
 
dos
 
endpoints,
 
permitindo
 
a
 
tomada
 
de
 
ações
 
adequadas.
 
Um
 
módulo
 
de
 
checagem
 
de
 
regras
 
(
rules
 
engine
)
 
será
 
desenvolvido
 
para
 
detectar
 
esses
 
eventos
 
para
 
notificação
 
aos
 
usuários
 
para
 
disponibilizar
 
nas
 
visualizações
 
integradas
 
à
 
UI.
 
Por
 
fim,
 
o
 
sistema
 
recomendará
 
ações
 
e
 
scripts
 
de
 
execução
 
que
 
possam
 
ser
 
aplicados
 
diretamente
 
nas
 
APIs
 
dos
 
produtos
 
de
 
armazenamento.
 
Essa
 
integração
 
com
 
os
 
produtos
 
seguirá
 
o
 
mapeamento
 
definido
 
na
 
etapa
 
1.3.
 Duração  prevista:  03/2026  –  06/2026  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Full-stack
  
1,Desenvolvedor
 
Full-stack
 
2.
  Fase   3:  Desenvolvimento  e  Implementação    Etapa  3.1  -  Desenvolvimento  de  procedimentos  ETL  Esta  etapa  compreenderá  o  desenvolvimento  dos  componentes  centrais  do  sistema,  abrangendo  
a
 
implementação
 
dos
 
módulos
 
de
 
ETL
 
aprimorado,
 
analytics,
 
auto-reclamação,
 
observabilidade
 
e
 
dashboards.
 
Serão
 
realizadas
 
integrações
 
com
 
os
 
novos
 
produtos
 
de
 
armazenamento
 
e
 
serão
 
desenvolvidos
 
mecanismos
 
de
 
auditoria
 
e
 
logging
 
para
 
rastreabilidade
 
das
 
ações.
 
O
 
time
 
de
 
DevOps
 
atuará
 
na
 
criação
 
e
 
automação
 
dos
 
pipelines
 
de
 
CI/CD,
 
garantindo
 
a
 
entrega
 
contínua
 
de
 
versões
 
testadas
 
e
 
estáveis.
 
Serão
 
conduzidos
 
testes
 
unitários,
 
de
 
integração,
 
de
 
desempenho
 
e
 
de
 
segurança
 
para
 
validar
 
o
 
comportamento
 
do
 
sistema
 
sob
 
diferentes
 
cenários
 
operacionais.
  Duração  prevista:  05/2026  –  08/2026

Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,
 
Especialista
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Especialista
 
em
 
Banco
 
de
 
Dados
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Full-stack
  
1,
 
Desenvolvedor
 
Full-stack
 
2.
  Etapa  3.2  -  Desenvolvimento  do  Backend  (melhorias  e  novos  recursos)  Esta  etapa  compreenderá,  no  contexto  do  backend  do  sistema,  o  desenvolvimento  de  
aprimoramentos
 
em
 
funcionalidades
 
já
 
presentes
 
e
 
de
 
novas
 
funcionalidades,
 
definidas
 
na
 
etapa
 
1.4.
 
O
 
desenvolvimento
 
iniciará
 
seguindo
 
a
 
arquitetura
 
proposta
 
no
 
ciclo
 
anterior
 
e
 
depois
 
adotará
 
as
 
novas
 
definições
 
estabelecidas
 
nas
 
etapas
 
2.3
 
e
 
2.4.
 Duração  prevista:  03/2026  –  02/2027  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,
 
Especialista
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Especialista
 
em
 
Banco
 
de
 
Dados
 
,
 
Desenvolvedor
 
Jr.
 
1
,
Desenvolvedor
 
Jr.
 
2,
 
Desenvolvedor
 
Jr.
 
3
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Full-stack
 
1,
 
Desenvolvedor
 
Full-stack
 
2.
  Etapa  3.3  -  Desenvolvimento  do  Frontend  (melhorias  e  novos  recursos)  Esta  etapa  compreenderá,  no  contexto  do  frontend  do  sistema,  o  desenvolvimento  de  
aprimoramentos
 
em
 
funcionalidades
 
já
 
presentes
 
e
 
de
 
novas
 
funcionalidades,
 
definidas
 
na
 
etapa
 
1.4.
 
O
 
desenvolvimento
 
iniciará
 
seguindo
 
a
 
arquitetura
 
proposta
 
no
 
ciclo
 
anterior
 
e
 
depois
 
adotará
 
as
 
novas
 
definições
 
estabelecidas
 
na
 
etapa
 
1.3.
 
Esta
 
etapa
 
considera
 
também
 
as
 
concepções
 
elaboradas
 
e
 
validadas
 
na
 
etapa
 
2.2.
 Duração  prevista:  03/2026  –  02/2027  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Visualização
 
,
 
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,
 
Especialista
 
em
 
Visualização
 
,
 
Desenvolvedor
 
Jr.
 
1
,
 
Desenvolvedor
 
Jr.
 
2,
 
Desenvolvedor
 
Jr.
 
3,
 
UI/UX
 
Designer
 
Jr.
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Designer
 
de
 
UI/UX,
 
Desenvolvedor
 
Full-stack
  
1,
 
Desenvolvedor
 
Full-stack
 
2.
  Etapa  3.4  -  Teste  de  Sistema  Durante  toda  a  fase  de  desenvolvimento,  serão  realizados  testes  unitários  e  de  integração  para  
validar
 
a
 
funcionalidade
 
e
 
confiabilidade
 
dos
 
componentes
 
do
 
backend
 
e
 
frontend.
 
Esses
 
testes
 
garantirão
 
que
 
cada
 
módulo
 
funcione
 
conforme
 
esperado
 
seguindo
 
as
 
diretrizes
 
de
 
qualidade
 
de
 
código
 
estabelecidas
 
pela
 
Dell,
 
individualmente
 
e
 
dentro
 
do
 
sistema
 
integrado.
 
A
 
equipe
 
da
 
Dell
 
acompanhará
 
e
 
validará
 
os
 
testes,
 
assegurando
 
conformidade
 
com
 
os
 
padrões
 
de
 
segurança
 
e
 
compliance
 
da
 
empresa.
 
Além
 
dos
 
testes
 
obrigatórios
 
pelo
 
padrão
 
Dell,
 
serão
 
realizados
 
testes
 
manuais
 
por
 
uma
 
equipe
 
direcionada,
 
que
 
também
 
trabalhará
 
no
 
desenvolvimento
 
de
 
testes
 
automatizados
 
de
 
integração
 
e
 
ponta-a-ponta.
 Duração  prevista:  03/2026  –  02/2027  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Arquitetura
 
de
 
Software,
 
Testador
 
Jr.
 
1
,
Testador
 
Jr.
 
2,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Full-stack
 
1,
 
Desenvolvedor
 
Full-stack
 
2.
  Etapa  3.5  -  Preparação  para  Implantação  em  Produção  Nesta  etapa  ocorrerá  o  desenvolvimento  e  configuração  da  pipeline  de  implantação  
automatizada,
 
garantindo
 
uma
 
transição
 
segura
 
e
 
controlada
 
da
 
solução
 
do
 
ambiente
 
de
 
testes
 
para
 
o
 
ambiente
 
de
 
produção.
 
O
 
processo
 
seguirá
 
os
 
requisitos
 
estabelecidos
 
para
 
uma
 
implantação
 
estável,
 
incluindo
 
validações
 
técnicas
 
e
 
avaliações
 
de
 
conformidade
 
realizadas
 
previamente.
 
A
 
equipe
 
de
 
desenvolvimento
 
permanecerá
 
disponível
 
para
 
apoiar
 
e
 
acompanhar
 
a

execução  dessa  implantação,  conforme  a  equipe  da  Dell  decidir  avançar  para  o  uso  produtivo  do  
sistema.
 
Dessa
 
forma,
 
esta
 
etapa
 
assegurará
 
que
 
a
 
solução
 
SAAR
 
II
 
esteja
 
preparada
 
para
 
operar
 
de
 
forma
 
contínua,
 
confiável
 
e
 
aderente
 
às
 
normas
 
corporativas.
 Duração  prevista:  03/2026  –  02/2027  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,Especialista
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Testador
 
Jr.
 
1
 
Testador
 
Jr.
 
2
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Full-stack
 
1,
 
Desenvolvedor
 
Full-stack
 
2.
  Etapa  3.6  -  Transferência  de  Tecnologia  A  transferência  de  tecnologia  ocorrerá  ao  longo  de  toda  a  execução  do  projeto,  por  meio  de  
reuniões
 
periódicas
 
com
 
a
 
equipe
 
da
 
Dell,
 
nas
 
quais
 
o
 
conhecimento
 
será
 
continuamente
 
compartilhado
 
e
 
discutido.
 
Toda
 
a
 
documentação
 
técnica
 
e
 
de
 
desenvolvimento
 
será
 
mantida
 
atualizada,
 
de
 
modo
 
a
 
garantir
 
autonomia
 
total
 
da
 
Dell
 
na
 
operação
 
e
 
evolução
 
da
 
solução
 
entregue.
 
Além
 
disso,
 
serão
 
produzidos
 
e
 
disponibilizados
 
manuais
 
do
 
usuário,
 
guias
 
de
 
operação
 
e
 
demais
 
materiais
 
necessários
 
ao
 
correto
 
entendimento
 
do
 
fluxo
 
de
 
trabalho
 
implementado,
 
facilitando
 
o
 
uso
 
e
 
a
 
manutenção
 
do
 
produto.
 
Esses
 
artefatos
 
serão
 
organizados
 
e
 
armazenados
 
no
 
Confluence,
 
garantindo
 
acesso
 
fácil
 
e
 
centralizado
 
para
 
as
 
equipes
 
responsáveis,
 
reforçando
 
assim
 
os
 
objetivos
 
de
 
transferência
 
contínua
 
de
 
conhecimento
 
e
 
sustentabilidade
 
tecnológica
 
do
 
SAAR
 
II.
 Duração  prevista:  03/2026  –  02/2027  Participantes:  Coordenador  de  Projetos  ,  Pesquisador  em  Engenharia  de  Software  ,  
Pesquisador
 
em
 
Ciência
 
de
 
Dados
 
,
 
Pesquisador
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Pesquisador
 
em
 
Visualização
 
,
 
Pesquisador
 
em
 
Arquitetura
 
de
 
Software
 
,
 
Especialista
 
em
 
Engenharia
 
de
 
Dados
 
,
 
Especialista
 
em
 
Banco
 
de
 
Dados
 
,
 
Especialista
 
em
 
Visualização
 
,
 
Desenvolvedor
 
Jr.
 
1
,
 
Desenvolvedor
 
Jr.
 
2
,
 
Desenvolvedor
 
Jr.
 
3
,
 
UI/UX
 
Designer
 
Jr.
 
,
 
Testador
 
Jr.
 
1
 
,
 
Testador
 
Jr.
 
 
2
 
,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Designer
 
de
 
UI/UX,
 
Desenvolvedor
 
Full-stack
 
1,
 
Desenvolvedor
 
Full-stack
 
2.
 
2.6.  Duração   
Data  de  início:  01/03/2026  Data  de  estimada  de  término:  28/02/2027   
2.7.  Resultados  Esperados    O  projeto  FY27  entregará  uma  versão  maturada  e  de  produção  da  plataforma  SAAR,  com  foco  
em
 
integração
 
ampla,
 
previsibilidade
 
de
 
consumo
 
e
 
governança
 
de
 
dados.
  Os  principais  resultados  são:  ●  Integração  completa  do  ETL  com  os  produtos  Unity ,  PowerScale  (Isilon) ,  PowerFlex  e  
demais
 
plataformas
 
Dell;
 ●  Ampliação  das  análises  com  base  em  metadados  de  usuários,  aplicações  e  classes  de  
uso;
 ●  Implementação  de  um  processo  estruturado  de  auto-reclamação  automatizada ;  ●  Entrega  de  um  dashboard  de  observabilidade  consolidado;  ●  Implementação  de  suporte  DevOps  e  CI/CD ;  ●  Documentação  técnica,  manuais  de  uso  e  transferência  de  tecnologia  para  a  Dell;  ●  1  software  com  inovação  tecnológica  e  1  publicação  científica  com  resultados  do  
projeto.

2.8.  Indicadores  de  Resultados  Esperados  (§  2º,  art.  24,  Decreto  nº  5.906/2006)
  
1.  Patentes  depositadas  no  Brasil  e  no  exterior   Quantas  patentes  se  esperam  gerar?  Número  de  patentes  
☐  
2.  Concessão  de  co-titularidade  ou  de  participação  nos  resultados  da  pesquisa  e  desenvolvimento  às  instituições  convenentes  
☐  
3.  Protótipos,  processos,  softwares  e  produtos  que  incorporem  inovação  científica  ou  tecnológica   
Espera-se  gerar  1  software.  
x  
4.  Publicações  científicas  e  tecnológicas  em  periódicos  ou  eventos  científicos  com  revisão  pelos  pares.   Quantas  publicações  se  espera  gerar?  Espera-se  gerar  1  publicação.  
x  
5.  Dissertações  e  teses  defendidas.   ☐

3.  Dos  Recursos  Necessários  ao  Desenvolvimento  do  Projeto  
3.1  Introdução  
 Os  recursos  para  o  projeto  “ Storage  Analytics  and  Auto-Reclamation  II ”  foram  estimados  com  
base
 
em
 
metodologias
 
diferentes
 
dependendo
 
de
 
cada
 
rubrica.
 
Os
 
recursos
 
humanos
 
diretos
 
e
 
indiretos
 
foram
 
estimados
 
em
 
horas
 
mensais,
 
com
 
base
 
na
 
experiência
 
do
 
coordenador
 
da
 
instituição
 
e
 
no
 
escopo
 
do
 
projeto.
 
As
 
demais
 
rubricas
 
foram
 
estimadas
 
por
 
meio
 
de
 
cotações
 
com
 
fornecedores
 
e
 
a
 
partir
 
da
 
larga
 
experiência
 
do
 
coordenador
 
e
 
da
 
equipe
 
com
 
gestão
 
de
 
projetos
 
de
 
pesquisa
 
e
 
desenvolvimento
 
no
 
contexto
 
da
 
Lei
 
de
 
Informática.
 
3.2  Recursos  Humanos  Diretos  (Decreto  nº  5.906/2006,  art.  25,  inciso  III)  
Função:  Coordenador  do  Projeto  Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Profissional  responsável  pela  coordenação  científica  e  
técnica
 
do
 
projeto,
 
realizando
 
a
 
orientação
 
científica
 
para
 
a
 
publicação
 
de
 
artigos,
 
orientação
 
de
 
trabalhos
 
relacionadas
 
às
 
temáticas
 
deste
 
projeto,
 
definição
 
de
 
metodologia
 
e
 
instrumentos
 
utilizados
 
para
 
a
 
construção
 
das
 
tecnologias,
 
realização
 
de
 
pesquisas,
 
revisão
 
bibliográfica,
 
e
 
acompanhamento
 
técnico
 
de
 
todos
 
os
 
artefatos
 
gerados
 
para
 
a
 
construção
 
das
 
tecnologias
 
previstas.
 Horas  trabalhadas:  192h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  90.000,00   Função:  Pesquisador  em  Engenharia  de  Dados  Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Responsável  pela  condução  das  pesquisas  
relacionadas
 
à
 
Engenharia
 
de
 
Dados,
 
analisando
 
os
 
dados
 
coletados
 
pela
 
equipe
 
do
 
projeto,
 
sejam
 
eles
 
estruturados
 
ou
 
não-estruturados,
 
para
 
extração
 
de
 
conhecimento,
 
detecção
 
de
 
padrões
 
e/ou
 
obtenção
 
de
 
variáveis
 
para
 
possíveis
 
tomadas
 
de
 
decisão.
 Horas  trabalhadas:  192h  Total  do  dispêndio  (remuneração  total  com  encargos) :   R$  66.000,00   Função:  Pesquisador  em  Visualização  de  Dados  Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Responsável  condução  das  pesquisas  necessárias  e  
pela
 
criação
 
dos
 
painéis
 
de
 
visualização
 
dos
 
dados
 
resultantes
 
dos
 
das
 
análises
 
dos
 
dados.
 
Atuará,
 
também,
 
como
 
consultor
 
científico
 
nestes
 
tópicos,
 
orientando
 
o
 
trabalho
 
dos
 
pesquisadores
 
em
 
visualização
 
e
 
equipe
 
de
 
design.

Horas  trabalhadas:  192h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  66.000,00   Função:  Pesquisador  em  Engenharia  de  Software  Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Responsável  pela  condução  das  reuniões  de  
compreensão
 
do
 
contexto
 
técnico
 
do
 
projeto,
 
bem
 
como
 
pelo
 
levantamento
 
de
 
requisitos
 
junto
 
ao
 
time
 
da
 
Dell
 
e
 
pela
 
criação,
 
manutenção
 
e
 
priorização
 
do
 
backlog
 
de
 
trabalho.
 
Também
 
será
 
responsável
 
pelo
 
acompanhamento
 
das
 
cerimônias
 
de
 
gerenciamento
 
do
 
projeto
 
(
sprint
 
planning
,
 
daily
 
scrum
,
 
sprint
 
review
 
e
 
sprint
 
retrospective
)
 
em
 
parceria
 
com
 
o
 
Gerente
 
de
 
Projetos
 
e
 
o
 
Analista
 
de
 
Requisitos.
 
Responsável
 
pela
 
condução
 
do
 
desenho
 
e
 
implementação
 
da
 
arquitetura
 
da
 
solução,
 
e
 
de
 
acompanhar
 
a
 
adequação
 
das
 
soluções
 
ao
 
controle
 
de
 
qualidade
 
da
 
Dell.
 Horas  trabalhadas:  192h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  66.000,00   Função:  Pesquisador  em  Ciência  de  Dados  Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projet o:  Responsável  pela  condução  das  pesquisas  
relacionadas
 
às
 
técnicas
 
e
 
métodos
 
de
 
Ciência
 
de
 
Dados
 
que
 
serão
 
utilizados
 
no
 
projeto
.
 
Atuará,
 
também,
 
como
 
consultor
 
científico
 
nos
 
tópicos
 
de
 
Ciência
 
de
 
Dados
 
e
 
na
 
orientação
 
dos
 
demais
 
pesquisadores
 
em
 
Ciência
 
e
 
Engenharia
 
de
 
Dados.
 Horas  trabalhadas:  192h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  66.000,00   Função:  Especialista  em  Engenharia  de  Dados  Formação:  Superior  com  Mestrado  ou  Doutorando   Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:
 
Responsável  por  implementar  como  consumir  os  dados  
brutos
 
seguida
 
por
 
um
 
pré-processamento
 
rigoroso.
 
Além
 
de
 
implementar
 
unificação
 
de
 
padrões
 
(ex.,
 
conversões
 
de
 
medidas
 
de
 
armazenamento),
 
remoção
 
de
 
dados
 
duplicados,
 
filtragem
 
e
 
verificação
 
de
 
integridade.
 
Além
 
da
 
transformação,
 
o
 
profissional
 
deve
 
ser
 
responsável
 
pela
 
etapa
 
de
 
modelagem
 
e
 
armazenamento
 
dos
 
dados
 
utilizando
 
ferramentas
 
de
 
orquestração
 
como,
 
por
 
exemplo,
 
o
 
Apache
 
AirFlow
 
para
 
garantir
 
a
 
automação
 
e
 
monitoramento
 
do
 
ciclo
 
de
 
vida
 
da
 
informação.
 
Por
 
fim,
 
é
 
esperado
 
que
 
os
 
dados
 
processados
 
sejam
 
persistidos
 
em
 
plataformas
 
relacionais
 
de
 
modo
 
que
 
seja
 
garantida
 
a
 
disponibilidade,
 
confiabilidade
 
e
 
integridade.
 Horas  trabalhadas:  960h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  38.400,00

Função:  Especialista  em  Visualização   Formação:  Superior  com  Mestrando,  Mestrado  ou  Doutorando   Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:
 
Responsável  pela  concepção,  implementação  e  
avaliação
 
de
 
interfaces
 
interativas
 
e
 
painéis
 
visuais
 
avançados
 
para
 
análise
 
e
 
interpretação
 
dos
 
resultados
 
produzidos
 
pelo
 
projeto.
 
Sua
 
principal
 
responsabilidade
 
será
 
traduzir
 
informações
 
complexas
 
em
 
representações
 
visuais
 
intuitivas,
 
favorecendo
 
a
 
compreensão
 
e
 
comunicação
 
dos
 
achados
 
científicos
 
e
 
dos
 
indicadores
 
de
 
desempenho
 
das
 
soluções
 
desenvolvidas.
 
Horas  trabalhadas:  960h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  38.400,00   Função:  Pesquisador  em  Arquitetura  de  Software  Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:
 
Responsável  pelas  atividades  de  auxílio  de  análise  de  
viabilidade,
 
seleção
 
de
 
tecnologias,
 
desenho
 
e
 
especificação
 
da
 
arquitetura
 
da
 
solução
 
e
 
apoio
 
à
 
equipe
 
de
 
desenvolvimento.
 
Horas  trabalhadas:  192h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  66.000,00   Função:  Especialista  em  Banco  de  Dados   Formação:  Superior  com  Mestrado,  Doutorando  ou  Doutor  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Responsável  pela  garantia  do  desempenho,  
escalabilidade
 
e
 
integridade
 
da
 
infraestrutura
 
de
 
dados.
 
Sua
 
atuação
 
se
 
concentrará
 
na
 
otimização
 
do
 
modelo
 
de
 
dados
 
para
 
suportar
 
o
 
processamento
 
contínuo
 
de
 
dados
 
históricos
 
reportados
 
pelas
 
diversas
 
plataformas
 
de
 
armazenamento.
 
A
 
expertise
 
técnica
 
é
 
necessária
 
para
 
refinar
 
o
 
esquema
 
de
 
dados,
 
otimizar
 
consultas
 
complexas
 
e
 
assegurar
 
a
 
manutenibilidade
 
e
 
rastreabilidade
 
da
 
solução
 
durante
 
as
 
fases
 
de
 
desenvolvimento,
 
testes
 
e
 
transferência
 
de
 
conhecimento
 
para
 
a
 
equipe. Horas  trabalhadas:  960h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  66.000,00   Função:  Desenvolvedor  Jr.  1  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Profissional  responsável  pela  implementação  de  
correções,
 
melhorias
 
e
 
novas
 
funcionalidades
 
relacionadas
 
às
 
aplicações
 
front-end
 
e
 
aos

serviços  back-end.  Deve  também  implementar  testes  unitários  e  auxiliar  os  testadores  nas  
devolutivas
 
dos
 
testes
 
para
 
que
 
se
 
possa
 
retestar
 
no
 
menor
 
tempo
 
possível,
 
visando
 
produzir
 
uma
 
plataforma
 
segura
 
e
 
estável.
 
Também
 
suporta
 
na
 
execução
 
de
 
ajustes
 
finais
 
na
 
solução,
 
possibilitando
 
a
 
transferência
 
tecnológica
 
para
 
a
 
equipe.
 Horas  trabalhadas:  1.200h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Desenvolvedor  Jr.  2  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Profissional  responsável  pela  implementação  de  
correções,
 
melhorias
 
e
 
novas
 
funcionalidades
 
relacionadas
 
às
 
aplicações
 
front-end
 
e
 
aos
 
serviços
 
back-end.
 
Deve
 
também
 
implementar
 
testes
 
unitários
 
e
 
auxiliar
 
os
 
testadores
 
nas
 
devolutivas
 
dos
 
testes
 
para
 
que
 
se
 
possa
 
retestar
 
no
 
menor
 
tempo
 
possível,
 
visando
 
produzir
 
uma
 
plataforma
 
segura
 
e
 
estável.
 
Também
 
suporta
 
na
 
execução
 
de
 
ajustes
 
finais
 
na
 
solução,
 
possibilitando
 
a
 
transferência
 
tecnológica
 
para
 
a
 
equipe.
 Horas  trabalhadas:  1.200h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Desenvolvedor  Jr.  3  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Profissional  responsável  pela  implementação  de  
correções,
 
melhorias
 
e
 
novas
 
funcionalidades
 
relacionadas
 
às
 
aplicações
 
front-end
 
e
 
aos
 
serviços
 
back-end.
 
Deve
 
também
 
implementar
 
testes
 
unitários
 
e
 
auxiliar
 
os
 
testadores
 
nas
 
devolutivas
 
dos
 
testes
 
para
 
que
 
se
 
possa
 
retestar
 
no
 
menor
 
tempo
 
possível,
 
visando
 
produzir
 
uma
 
plataforma
 
segura
 
e
 
estável.
 
Também
 
suporta
 
na
 
execução
 
de
 
ajustes
 
finais
 
na
 
solução,
 
possibilitando
 
a
 
transferência
 
tecnológica
 
para
 
a
 
equipe.
 Horas  trabalhadas:  1.200h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  UI/UX  Designer  Jr.  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Responsável  pelas  atividades  relacionadas  a  
planejamento,
 
prototipação,
 
implementação
 
de
 
interfaces
 
e
 
experiência
 
de
 
usuário.
 
Através
 
do
 
uso
 
das
 
boas
 
práticas
 
e
 
conceitos
 
de
 
User
 
Experience
 
(UX)
 
e
 
IHC,
 
auxiliará
 
na
 
elicitação
 
de
 
requisitos
 
e
 
prototipação
 
da
 
interface
 
que
 
auxiliará
 
a
 
equipe
 
de
 
engenharia
 
de
 
software
 
no
 
desenvolvimento
 
do
 
front-end
 
do
 
projeto.
 
Também
 
fará
 
benchmarks
 
de
 
soluções
 
existentes
 
e
 
conduzirá
 
reuniões
 
de
 
prototipação
 
e
 
entrevistas
 
com
 
os
 
usuários.
 Horas  trabalhadas:  1.200h

Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Testador  Jr.  1  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Profissional  responsável  pela  implementação  e  
realização
 
dos
 
testes
 
e
 
avaliação
 
dos
 
riscos
 
e
 
impactos
 
dos
 
testes.
 
Em
 
conjunto
 
com
 
os
 
resultados
 
dos
 
testes
 
da
 
etapa
 
anterior,
 
este
 
profissional
 
também
 
deverá
 
acompanhar
 
os
 
relatórios
 
gerados
 
pelas
 
ferramentas
 
de
 
análise
 
de
 
código
 
a
 
fim
 
de
 
evoluir
 
a
 
solução
 
desenvolvida
 
e
 
torná-la
 
compatível
 
com
 
as
 
necessidades
 
do
 
público-alvo,
 
além
 
de
 
possibilitar
 
a
 
identificação
 
de
 
possíveis
 
falhas
 
e
 
trechos
 
de
 
código
 
que
 
podem
 
ser
 
aprimorados
 
(Garantia
 
de
 
Qualidade).
 
Finalmente,
 
este
 
profissional
 
será
 
responsável
 
pela
 
manutenção
 
do
 
pipeline
 
do
 
projeto,
 
garantindo
 
que
 
esteja
 
sempre
 
disponível
 
e
 
conforme
 
as
 
recomendações
 
da
 
Dell.
 Horas  trabalhadas:  1.200h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Testador  Jr.  2  Formação:  Superior  Mestrando  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Profissional  responsável  pela  implementação  e  
realização
 
dos
 
testes
 
e
 
avaliação
 
dos
 
riscos
 
e
 
impactos
 
dos
 
testes.
 
Em
 
conjunto
 
com
 
os
 
resultados
 
dos
 
testes
 
da
 
etapa
 
anterior,
 
este
 
profissional
 
também
 
deverá
 
acompanhar
 
os
 
relatórios
 
gerados
 
pelas
 
ferramentas
 
de
 
análise
 
de
 
código
 
a
 
fim
 
de
 
evoluir
 
a
 
solução
 
desenvolvida
 
e
 
torná-la
 
compatível
 
com
 
as
 
necessidades
 
do
 
público-alvo,
 
além
 
de
 
possibilitar
 
a
 
identificação
 
de
 
possíveis
 
falhas
 
e
 
trechos
 
de
 
código
 
que
 
podem
 
ser
 
aprimorados
 
(Garantia
 
de
 
Qualidade).
 
Finalmente,
 
este
 
profissional
 
será
 
responsável
 
pela
 
manutenção
 
do
 
pipeline
 
do
 
projeto,
 
garantindo
 
que
 
esteja
 
sempre
 
disponível
 
e
 
conforme
 
as
 
recomendações
 
da
 
Dell.
 Horas  trabalhadas:  1.200h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  27.000,00   Função:  Gerente  de  Projetos  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Profissional  responsável  pela  realização  das  atividades  
de
 
gerenciamento
 
do
 
escopo
 
(documentação
 
do
 
escopo
 
e
 
controle
 
de
 
mudanças
 
do
 
projeto),
 
cronograma
 
(planejamento
 
das
 
atividades
 
e
 
atualização
 
de
 
status
 
com
 
o
 
time
 
do
 
projeto),
 
custos
 
(mapeamento
 
de
 
custos
 
necessários
 
para
 
suportar
 
a
 
realização
 
das
 
atividades
 
da
 
equipe),
 
aquisições
 
(mapeamento
 
das
 
aquisições
 
necessárias
 
para
 
realização
 
do
 
escopo),
 
recursos
 
humanos
 
(gerenciamento
 
das
 
atividades
 
da
 
equipe
 
do
 
projeto),
 
dentre
 
outras
 
áreas,
 
para
 
que
 
os
 
resultados
 
previstos
 
neste
 
projeto
 
fossem
 
alcançados
 
no
 
tempo,
 
na
 
qualidade
 
e
 
no
 
orçamento
 
previstos
 
para
 
este
 
projeto.
 Horas  trabalhadas:  768h

Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  133.421,36   Função:  Analista  de  Requisitos  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  proj eto:  Profissional  responsável  pela  realização  das  
especificações
 
funcionais
 
para
 
o
 
desenvolvimento
 
da
 
tecnologia
 
prevista
 
no
 
escopo
 
deste
 
projeto,
 
participando
 
das
 
atividades
 
de
 
levantamento
 
de
 
requisitos.
 
Além
 
disso,
 
atuará
 
nas
 
entrevistas,
 
condução
 
de
 
reuniões
 
para
 
planejamento,
 
revisão
 
e
 
apresentação
 
dos
 
resultados
 
dos
 
Sprints,
 
além
 
disso,
 
atuará
 
diretamente
 
com
 
o
 
Coordenador
 
do
 
Projeto
 
e
 
Gerente
 
de
 
Projetos
 
para
 
acompanhar
 
o
 
cronograma
 
e
 
preparar
 
o
 
planejamento
 
das
 
entregas.
 Horas  trabalhadas:  1920h  
Total
 
do
 
dispêndio
 
(remuneração
 
total
 
com
 
encargos)
:
 
R$
 
133.056,30
  Função:  UX/UI  Designer  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  proje to:  Responsável  pelas  atividades  relacionadas  a  
planejamento,
 
prototipação,
 
implementação
 
de
 
interfaces
 
e
 
experiência
 
de
 
usuário.
 
Através
 
do
 
uso
 
das
 
boas
 
práticas
 
e
 
conceitos
 
de
 
User
 
Experience
 
(UX)
 
e
 
IHC,
 
auxiliará
 
na
 
elicitação
 
de
 
requisitos
 
e
 
prototipação
 
da
 
interface
 
que
 
auxiliará
 
a
 
equipe
 
de
 
engenharia
 
de
 
software
 
no
 
desenvolvimento
 
do
 
front-end
 
do
 
projeto.
 
Também
 
fará
 
benchmarks
 
de
 
soluções
 
existentes
 
e
 
conduzirá
 
reuniões
 
de
 
prototipação
 
e
 
entrevistas
 
com
 
os
 
usuários.
 Horas  trabalhadas:  1920h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  112.344,21   Função:  Desenvolvedor  Full-stack  1  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Responsável  por  desenvolver  as  aplicações  e  as  
técnicas
 
de
 
front-end
 
e
 
back-end
 
que
 
foram
 
definidas
 
pelos
 
pesquisadores
 
e
 
especialistas.
 
Deve
 
implementar
 
os
 
testes
 
unitários
 
e
 
de
 
integração,
 
além
 
de
 
auxiliar
 
os
 
testadores
 
nas
 
devolutivas
 
dos
 
testes
 
para
 
que
 
se
 
possa
 
fazer
 
o
 
teste
 
novamente
 
no
 
menor
 
tempo
 
possível,
 
visando
 
produzir
 
uma
 
plataforma
 
segura
 
e
 
estável.
 
Atua
 
no
 
desenvolvimento
 
da
 
solução,
 
implementando
 
as
 
novas
 
interfaces
 
da
 
solução,
 
bem
 
como
 
realizando
 
as
 
integrações
 
e
 
o
 
desenvolvimento
 
dos
 
serviços
 
do
 
back-end.
 
Também
 
é
 
colaborador
 
responsável
 
pela
 
documentação
 
do
 
front-end
 
e
 
do
 
back-end
 
do
 
projeto
 
e
 
suporta
 
a
 
execução
 
de
 
ajustes
 
finais
 
na
 
solução,
 
possibilitando
 
a
 
transferência
 
tecnológica
 
para
 
a
 
Dell.
 Horas  trabalhadas:  1920h  
Total
 
do
 
dispêndio
 
(remuneração
 
total
 
com
 
encargos)
:
 
R$
 
185.792,30

Função:  Desenvolvedor  Full-stack  2  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto :    Responsável  por  desenvolver  as  aplicações  e  as  
técnicas
 
de
 
front-end
 
e
 
back-end
 
que
 
foram
 
definidas
 
pelos
 
pesquisadores
 
e
 
especialistas.
 
Deve
 
implementar
 
os
 
testes
 
unitários
 
e
 
de
 
integração,
 
além
 
de
 
auxiliar
 
os
 
testadores
 
nas
 
devolutivas
 
dos
 
testes
 
para
 
que
 
se
 
possa
 
fazer
 
o
 
teste
 
novamente
 
no
 
menor
 
tempo
 
possível,
 
visando
 
produzir
 
uma
 
plataforma
 
segura
 
e
 
estável.
 
Atua
 
no
 
desenvolvimento
 
da
 
solução,
 
implementando
 
as
 
novas
 
interfaces
 
da
 
solução,
 
bem
 
como
 
realizando
 
as
 
integrações
 
e
 
o
 
desenvolvimento
 
dos
 
serviços
 
do
 
back-end.
 
Também
 
é
 
colaborador
 
responsável
 
pela
 
documentação
 
do
 
front-end
 
e
 
do
 
back-end
 
do
 
projeto
 
e
 
suporta
 
a
 
execução
 
de
 
ajustes
 
finais
 
na
 
solução,
 
possibilitando
 
a
 
transferência
 
tecnológica
 
para
 
a
 
Dell.
 Horas  trabalhadas:  1920h  
Total
 
do
 
dispêndio
 
(remuneração
 
total
 
com
 
encargos)
:
 
R$
 
94.515,06
  
3.3  Recursos  Humanos  Indiretos  (Decreto  nº  5.906/2006,  art.  25,  inciso  IV)  
Função:  Analista  Financeiro  
Formação:  Superior  
Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  
Atuação  e  justificativa  para  o  projeto:  Profissional  responsável  pelo  suporte  
administrativo
 
e
 
financeiro
 
para
 
realização
 
das
 
atividades
 
do
 
projeto,
 
como,
 
por
 
exemplo,
 
controle
 
das
 
folhas
 
dos
 
colaboradores
 
do
 
projeto,
 
controle
 
e
 
digitalização
 
de
 
documentação
 
dos
 
colaboradores,
 
organização
 
e
 
inclusão
 
do
 
banco
 
de
 
dados
 
dos
 
colaboradores,
 
cotação
 
e
 
solicitação
 
de
 
materiais
 
de
 
uso
 
do
 
projeto,
 
apoio
 
na
 
elaboração
 
do
 
RDA
 
do
 
projeto,
 
validações
 
de
 
ofícios,
 
arquivamento
 
de
 
documentos,
 
e
 
suporte
 
a
 
demais
 
atividades
 
administrativas
 
e
 
financeiras.
 
Horas  trabalhadas:  1920  h  
Total
 
do
 
dispêndio
 
(remuneração
 
total
 
com
 
encargos)
:
 
R
$
 
96.632,23
 
 
3.4  Viagens  (Decreto  nº  5.906/2006,  art.  25,  inciso  VII)  
Não  se  aplica.  
3.5  Serviços  Técnicos  (Decreto  nº  5.906/2006,  art.  25,  inciso  IX)  
Não  se  aplica.  
3.6  Equipamentos  e  Software  (Decreto  nº  5.906/2006,  art.  25,  inciso  I)  
Dispêndio  (Adequação):  04  Notebooks  Dell   —   Quantitativo  adequado  para  atender  às

atividades  da  equipe  do  projeto.  Tipo  de  Apropriação :  Equipamento  TICs  —  Aquisição  Descrição:  Notebook  Dell   —   Máquina  dedicada  à  equipe  do  projeto  para  realização  das  
atividades
 
de
 
desenvolvimento
 
e
 
teste
 
dos
 
algoritmos
 
e
 
funcionalidades
 
que
 
serão
 
desenvolvidas
 
durante
 
a
 
execução
 
deste
 
projeto,
 
com
 
configurações
 
iguais
 
ou
 
semelhantes:
 
Notebook
 
Dell
 
(Core
 
i7
 
13ª
 
geração,
 
RAM
 
32
 
GB,
 
SSD
 
1
 
TB,
 
Wi-Fi,
 
FHD,
 
Bat.
 
6
 
Cel.).
 Valor:  R$  28.000,00  Justificativa  (Pertinência):  Máquinas  dedicadas  à  equipe  do  projeto  para  realização  das  
atividades
 
de
 
pesquisa
 
e
 
desenvolvimento
 
inerentes
 
ao
 
escopo
 
do
 
projeto.
  Dispêndio  (Adequação):  3  unidades-chave  de  acesso  HSK  —   Quantitativo  adequado  em  
relação
 
os
 
novos
 
perfis
 
do
 
projeto
 Tipo  de  Apropriação :  Equipamento  Outros  —  Aquisição  Descrição:  Equipamento  utilizado  para  a  autenticação  ao  acesso  à  rede  Dell   Valor:  R$  600,00  Justificativa  (Pertinência):  Chaves  físicas  de  acesso  à  infraestrutura  da  rede  Dell.   Dispêndio  (Adequação):  3  unidades  licenças  Google  Workspace  Business  Standard  —   
Quantitativo
 
adequado
 
em
 
relação
 
os
 
novos
 
perfis
 
do
 
projeto
 Tipo  de  Apropriação :  Software  —  Licença  anual  Descrição:  Cessão  de  direito  ao  uso  de  licenças  Google,  necessária  para  acesso  às  
ferramentas
 
corporativas.
 Valor:  R$  2.700,00   Justificativa  (Pertinência):  Cessão  de  direito  ao  uso  de  licenças  G-suíte  basic  do  Google,  
necessária
 
para
 
acesso
 
do
 
às
 
ferramentas
 
corporativas
 
como:
 
Gmail,
 
Drive,
 
Agendas,
 
Pacote
 
Office
 
na
 
Nuvem,
 
entre
 
outras,
 
como
 
suporte
 
às
 
atividades
 
realizadas
 
em
 
todas
 
as
 
etapas
 
deste
 
projeto.
 
Será
 
utilizada
 
para
 
serviços
 
em
 
nuvem
 
da
 
Google
 
para
 
que
 
todos
 
os
 
colaboradores
 
do
 
projeto
 
tenham
 
melhor
 
desempenho
 
na
 
realização
 
das
 
atividades,
 
bem
 
como
 
suporte
 
à
 
realização
 
de
 
diversas
 
atividades
 
técnicas
 
do
 
projeto,
 
tais
 
como
 
a
 
construção
 
online
 
e
 
colaborativa
 
de
 
documentos,
 
relatórios
 
online
 
utilizados
 
na
 
realização
 
dos
 
testes
 
e
 
das
 
atividades
 
de
 
pesquisa,
 
além
 
de
 
viabilizar
 
um
 
processo
 
que
 
preconiza
 
maior
 
segurança
 
à
 
proteção
 
dos
 
dados,
 
considerando
 
que
 
as
 
contas
 
de
 
e-mail
 
utilizadas
 
para
 
comunicação
 
entre
 
os
 
membros
 
do
 
projeto
 
e
 
o
 
cliente,
 
são
 
gerenciadas
 
por
 
um
 
usuário
 
administrador.
 
3.7  Treinamento  (Decreto  nº  5.906/2006,  art.  25,  inciso  VIII)  
Não  se  aplica.  
3.8  Livros  /  Periódicos  Técnicos  (Decreto  nº  5.906/2006,  art.  25,  inciso  V)  
Não  se  aplica.  
3.9  Material  de  Consumo  (Decreto  nº  5.906/2006,  art.  25,  inciso  VI)  
Não  se  aplica.  
3.10  Obra  Civil  /  Construções  (Decreto  de  nº  5.906,  de  26  de  setembro  de  2006,  art.  
25º,
 
inciso
 
Il)
 
Não  se  aplica.  
3.11  Outros  Correlatos  (Decreto  nº  5.906/2006,  art.  25,  inciso  X)  
Não  se  aplica.

3.12  Custos  Incorridos  pela  instituição  
Discriminação  dos  principais  dispêndios  e  destinações:  Despesas  operacionais  incorridas  
pela
 
instituição
 
tais
 
como
 
despesas
 
decorrentes
 
das
 
atividades
 
administrativas
 
e
 
financeiras
 
realizadas
 
para
 
suporte
 
ao
 
Projeto.
 
Valor:  R$  354.098,73  
Justificativa:  São  considerados  como  custos  incorridos  os  valores  descritos  a  seguir,  conforme  
previsto
 
no
 
decreto
 
nº
 
6.405,
 
de
 
19
 
de
 
março
 
de
 
2008,
 
respeitando
 
o
 
limite
 
de
 
até
 
20%
 
do
 
montante
 
a
 
ser
 
gasto
 
no
 
projeto:
 
os
 
valores
 
com
 
constituição
 
de
 
reserva
 
a
 
ser
 
aplicada
 
em
 
pesquisa,
 
desenvolvimento
 
e
 
inovação
 
do
 
setor
 
de
 
tecnologias
 
da
 
informação
 
e
 
comunicação,
 
pela
 
UFC,
 
de
 
acordo
 
com
 
o
 
Art.
 
25,
 
§
 
5o.,
 
Decreto
 
5906/2006
 
que
 
somam
 
(R$
 
58.434,46)
;
 
os
 
valores
 
referentes
 
aos
 
custos
 
incorridos
 
para
 
o
 
desenvolvimento
 
do
 
projeto,
 
que
 
incluem
 
os
 
custos
 
de
 
10%
 
do
 
valor
 
total
 
do
 
projeto
 
(R$
 
146.086,15)
,
 
relativos
 
ao
 
interveniente
 
financeiro
 
FASTEF,
 
conforme
 
prerrogativa
 
da
 
Lei
 
no
 
8.958,
 
de
 
1994,
 
Decreto
 
8.240/14,
 
Lei
 
no
 
10.973/04,
 
Lei
 
13.243/16
 
e
 
Decreto
 
9.283/18;
 
bem
 
como
 
os
 
valores
 
referentes
 
aos
 
custos
 
incorridos
 
para
 
o
 
desenvolvimento
 
do
 
projeto
 
na
 
UFC
 
conforme
 
resolução
 
14/2022
 
-
 
CONSUNI,
 
que
 
totalizam
 
dos
 
custos
 
do
 
projeto
 
(R$
 
73.043,07)
 
-
 
calculados
 
pela
 
CPO/PROPLAD/UFC,
 
os
 
quais
 
deverão
 
ser
 
debitados
 
no
 
Código
 
28955-8
 
(Outros
 
Ressarcimentos),
 
na
 
Fonte
 
250
 
e
 
serão
 
realizados
 
conforme
 
os
 
repasses
 
que
 
a
 
empresa
 
fará,
 
e
 
a
 
FASTEF
 
se
 
obriga
 
a
 
transferi-lo
 
até
 
o
 
último
 
dia
 
útil
 
do
 
mês
 
seguinte
 
ao
 
da
 
arrecadação
 
de
 
cada
 
parcela.
 
Estes
 
valores
 
estão
 
previstos
 
como
 
cumprimento
 
das
 
obrigações
 
de
 
acordo
 
com
 
o
 
que
 
determina
 
a
 
legislação
 
vigente
 
incluindo,
 
mas
 
não
 
se
 
limitando
 
às
 
Leis
 
no.
 
8.248/91,
 
no.
 
10.176/2001
 
e
 
Lei.
  
no.
 
11.077/04
 
e
 
ao
 
Decreto
 
5.906/2006.
 
E
 
ainda
 
(R$72.928,58)
,
 
necessárias
 
para
 
possibilitar
 
a
 
realização
 
das
 
atividades
 
do
 
projeto,
 
tais
 
como:
 
seguro
 
de
 
vida
 
dos
 
bolsistas,
 
tarifas
 
bancárias,
 
ASO,
 
material
 
de
 
limpeza
 
de
 
ambiente,
 
manutenção
 
de
 
equipamentos
 
e
 
laboratórios,
 
correios,
 
sistemas
 
de
 
assinatura
 
em
 
plataforma
 
digital,
 
licenças
 
Google,
 
entre
 
outras
 
despesas.
 
 
3.13.  Quadros  Resumo  dos  Recursos  Necessários  ao  Desenvolvimento  do  Projeto  
 
  RH  Direto  RH  Indireto  Total  Nível  Superior  Médio  Superior  Médio  Quantidade  de  pessoas  15  5  1   21  Valor  (R$)  R$   1.248.929,23  R$  84.000,00  R$  96.632,23   R$  1.429.561,46  Total  de  horas  trabalhadas  
13.680  6.000  1.920   21.600  
 
Rubrica  Total  %  RH  Total  
R$  1.429.561,46  78,77%  Obras  Civis    Serviços  Técnicos    Livros  E  Periódicos  Técnicos    Outros  Correlatos    Equipamento  e  Software  
R$  31.300,00  1,72%  Material  De  Consumo    Treinamento    Viagens    Custo  Incorrido  (+  Fundo  de  Reserva)  
R$  354.098,73  19,51%  TOTAL  DE  DISPÊNDIOS  
 R$  1.814.960,20  100,00%

3.14.  Cronograma  Previsto  dos  Gastos  
Descrições  
mar./2026 abr./2026 mai./2026 jun./2026 jul./2026 ago./2026 set./2026 Rubricas  Previsto  Previsto  Previsto  Previsto  Previsto  Previsto   Previsto RH  Direto  
107.406,54
 
105.415,82
 
127.545,30
 
110.585,38
 
110.010,74
 
110.040,66
 
110.320,80
 RH  Indireto  
7.134,75
 
7.134,75
 
11.110,62
 
7.848,39
 
7.848,39
 
7.857,19
 
7.949,69
 Equipamentos  e  software  
31.300,00
       Material  de  consumo         Livros/periódicos  técnicos         Outros  correlatos         Custos  incorridos  pela  instituição  
35.350,52  27.281,17  33.608,86  28.707,20  28.567,92  28.577,30  28.667,63  Total  de  recursos  financeiros  (R$)  181.191,82 139.831,75 172.264,77 147.140,97 146.427,04 146.475,15 146.938,12 
 
Descrições  
out./2026 nov./2026 dez./2026 jan./2027 fev./2027 Total  %  Rubricas  Previsto  Previsto  Previsto  Previsto  Previsto  Previsto   RH  Direto  
110.320,80
 
110.320,80
 
110.320,80
 
110.320,80
 
110.320,80
 
1.332.929,23
 
73,4%
 RH  Indireto  
7.949,69
 
7.949,69
 
7.949,69
 
7.949,69
 
7.949,69
 
96.632,23
 
5,3%
 Equipamentos  e  software       
31.300,00
 
1,7%
 Material  de  consumo         Livros/periódicos  técnicos         Outros  correlatos         Custos  incorridos  pela  instituição  
28.667,63  28.667,63  28.667,63  28.667,63  28.667,63  354.098,73  19,51%  Total  de  recursos  financeiros  (R$)  146.938,12 146.938,12 146.938,12 146.938,12 146.938,12 1.814.960,20  100,00%

4.  Das  Disposições  Gerais  
O  presente  Plano  de  Trabalho  é  parte  integrante  do  XXº  ACORDO  DE  COOPERAÇÃO  
TÉCNICA
 
E
 
CIENTÍFICA
 
celebrado
 
entre
 
DELL,
 
UFC
 
e
 
ASTEF
.
    Fortaleza,  30  de  Outubro  de  2025.  
 
 
  
______________________________________________________________
 UNIVERSIDADE  FEDERAL  DO  CEARÁ  CNPJ:  07.272.636/0001-31  PROF.  CUSTÓDIO  LUIS  SILVA  ALMEIDA  Reitor  CPF:  078.883.173-91  CONVENIADA          ______________________________________________________________  A  FUNDAÇÃO  ASTEF  –  FUNDAÇÃO  DE  APOIO  A  SERVIÇOS  TÉCNICOS,  ENSINO  E  
FOMENTO
 
A
 
PESQUISAS
 CNPJ:  08.918.421/0001-08  Joaquim  Perucio  Pessoa  Filho  Diretor  Presidente  CPF:  404.268.903-53  INTERVENIENTE           ______________________________________________________________  DELL  COMPUTADORES  DO  BRASIL  LTDA  EMPRESA  Nome:  Mauricio  Helfer  CPF:  915.855.700-87
