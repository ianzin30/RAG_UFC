# RACK.pdf

Exclusivo  para  Lei  da  Informática   
PROJETO  DE  PESQUISA  E  DESENVOLVIMENTO  Plano  de  Trabalho  
Projeto  
Rack  Build  Deployment  Validation  and  Provisioning  II  
Coordenador  na  Instituição  
Paulo  Antonio  Leal  Rego  
 
Empresa  
Instituição  
Universidade  Federal  do  Ceará  -  UFC  Fundação  de  Apoio  a  Serviços  Técnicos,  Ensino  e  Fomento  a  Pesquisas  -  ASTEF  
Versão:  1.0  
Janeiro      2026

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
1.3.  Enquadramento  Atividades  do  Projeto  conforme  art.  2º,  Decreto  nº  
10.356/2020,
 
alterado
 
pelo
 
Decreto
 
nº
 
10.602/2021
 
  I  -  pesquisa  básica  -  pesquisa  experimental  ou  teórica  executada  primariamente  para  a  aquisição  de  conhecimento  novo  sobre  os  fundamentos  subjacentes  aos  fenômenos  e  fatos  observáveis,  sem  qualquer  aplicação  particular  ou  uso  em  vista;  
X  II  –  pesquisa  aplicada  -  pesquisa  original  realizada  para  adquirir  conhecimento  e  que  se  dirige  primariamente  a  um  objetivo  ou  a  um  alvo  prático  específico;  
 III  –  desenvolvimento  experimental  -  trabalho  sistemático,  baseado  em  conhecimento  preexistente  e  destinado  à  produção  de  novos  produtos  e  processos  ou  ao  aperfeiçoamento  dos  produtos  e  processos  existentes;  
 IV  -  inovação  tecnológica  -  a  implementação  de  produto,  quer  seja  ele  bem  ou  serviço,  ou  processo  tecnológico  novo,  ou  significativamente  aprimorado,  nos  termos  do  disposto  no  inciso  IV  do  caput  do  art.  2º  da  Lei  nº  10.973,  de  2  de  dezembro  de  2004;

2.  Descrição  do  Projeto  de  Pesquisa  e  Desenvolvimento  
2.1.
 
Introdução
 
 
A  transformação  digital  e  a  crescente  demanda  por  eficiência  na  gestão  de  data  centers  têm  
impulsionado
 
uma
 
nova
 
geração
 
de
 
soluções
 
voltadas
 
à
 
automação,
 
escalabilidade
 
e
 
padronização
 
de
 
infraestrutura.
 
Nesse
 
contexto,
 
o
 
paradigma
 
Infrastructure
 
as
 
Code
 
(IaC)
 
consolidou-se
 
como
 
uma
 
abordagem
 
essencial
 
para
 
a
 
administração
 
moderna
 
de
 
data
 
centers,
 
permitindo
 
que
 
componentes
 
de
 
hardware
 
e
 
software
 
sejam
 
tratados
 
como
 
código,
 
reduzindo
 
a
 
complexidade
 
operacional
 
e
 
aumentando
 
a
 
rastreabilidade.
   No  ciclo  anterior  do  projeto  (FY26),  o  time  da  Universidade  Federal  do  Ceará,  em  parceria  com  a  
Dell,
 
desenvolveu
 
o
 
MVP
 
(Minimum
 
Viable
 
Product)
 
do
 
sistema
 
Rack
 
Build
 
Deployment
 
Validation
 
and
 
Provisioning,
 
composto
 
por
 
módulos
 
que
 
viabilizaram
 
a
 
automação
 
da
 
validação
 
e
 
do
 
provisionamento
 
para
 
implantação
 
de
 
infraestrutura
 
de
 
data
 
centers
 
sob
 
a
 
perspectiva
 
de
 
Infrastructure
 
as
 
Code
 
(IaC).
 
O
 
sistema
 
automatiza
 
o
 
fluxo
 
de
 
trabalho
 
que
 
leva
 
à
 
montagem
 
de
 
um
 
rack,
 
desde
 
a
 
especificação
 
dos
 
requisitos
 
para
 
um
 
rack,
 
passando
 
por
 
sua
 
montagem
 
física
 
e
 
posterior
 
provisionamento,
 
com
 
a
 
instalação
 
dos
 
softwares
 
necessários
 
nos
 
equipamentos.
 
  Durante  o  processo  de  montagem,  são  feitas  validações  dos  requisitos  e  do  HBOM  ( Hardware  
Bill
 
of
 
Materials
)
 
gerado
 
pelo
 
sistema
 
a
 
partir
 
de
 
um
 
padrão
 
de
 
infraestrutura,
 
o
 
Big-1.
 
Para
 
tanto,
 
os
 
arquivos
 
a
 
serem
 
validados
 
foram
 
colocados
 
em
 
um
 
formato
 
padronizado
 
e
 
favorável
 
ao
 
processamento
 
computacional
 
e
 
as
 
regras
 
de
 
validação
 
foram
 
implementadas
 
utilizando
 
regras
 
adaptáveis.
 
O
 
provisionamento
 
da
 
infraestrutura
 
utilizou
 
ferramentas
 
de
 
IaC,
 
como
 
Terraform.
 
Além
 
disso,
 
foram
 
desenvolvidos
 
módulos
 
de
 
integração
 
às
 
ferramentas
 
de
 
CI/CD
 
e
 
emissão
 
de
 
tickets
 
existentes
 
e
 
um
 
módulo
 
que
 
automatiza
 
a
 
configuração
 
de
 
firmware
 
via
 
Redfish.
 
  Com  esses  avanços  técnico-científicos,  o  projeto  estabeleceu  uma  base  para  automação  e  
validação
 
de
 
infraestrutura
 
em
 
larga
 
escala,
 
atingindo
 
resultados
 
significativos
 
em
 
consistência
 
e
 
eficiência.
  O  escopo  proposto  para  o  ciclo  atual  (FY27)  contempla  a  evolução  da  solução  por  meio  de  duas  
frentes:
 
o
 
aprimoramento
 
dos
 
módulos
 
já
 
existentes
,
 
com
 
foco
 
em
 
otimização
 
de
 
desempenho,
 
aumento
 
de
 
cobertura
 
de
 
testes,
 
fortalecimento
 
da
 
estabilidade
 
operacional
 
e
 
preparação
 
para
 
uso
 
em
 
produção;
 
e
 
o
 
desenvolvimento
 
de
 
novas
 
funcionalidades
 
essenciais
,
 
incluindo
 
a
 
expansão
 
do
 
suporte
 
a
 
dispositivos
 
adicionais,
 
a
 
implementação
 
de
 
um
 
sistema
 
de
 
versionamento
 
de
 
configurações,
 
a
 
adoção
 
de
 
uma
 
plataforma
 
orquestradora
 
de
 
workflows
 
para
 
automação
 
ponta-a-ponta
 
e
 
a
 
criação
 
de
 
uma
 
interface
 
gráfica
 
para
 
facilitar
 
a
 
gestão
 
e
 
o
 
monitoramento
 
da
 
solução.
 
O
 
MVP
 
previsto
 
deverá
 
entregar
 
uma
 
versão
 
funcional
 
do
 
sistema,
 
com
 
implementação
 
programada
 
para
 
o
 
ciclo
 
de
 
desenvolvimento.

2.2.  Objetivo  e  Escopo   
O  objetivo  principal  deste  projeto  é  pesquisar,  aprimorar  e  expandir  o  sistema  de  validação  e  
provisionamento
 
automatizado
 
de
 
infraestrutura
 
de
 
data
 
centers
.
 
A
 
pesquisa
 
foca
 
na
 
otimização
 
de
 
módulos
 
desenvolvidos
 
no
 
ciclo
 
anterior
 
e
 
na
 
introdução
 
de
 
novas
 
capacidades,
 
com
 
ênfase
 
em
 
escalabilidade,
 
observabilidade
 
e
 
automação
 
inteligente.
 
O
 
escopo
 
deste
 
ciclo
 
do
 
projeto
 
(
FY27
)
 
está
 
estruturado
 
em
 
duas
 
frentes
 
de
 
pesquisa
 
e
 
desenvolvimento
 
interdependentes,
 
que
 
endereçam
 
o
 
aprimoramento
 
de
 
módulos
 
existentes
 
e
 
a
 
inovação
 
em
 
novas
 
funcionalidades.
 
Frente  1:  Otimização  de  Módulos  Estruturais  
Esta  frente  de  trabalho  foca  no  aprimoramento  dos  componentes  centrais  do  sistema,  visando  
garantir
 
desempenho,
 
confiabilidade
 
e
 
prontidão
 
para
 
o
 
ambiente
 
de
 
produção.
 
As
 
atividades
 
de
 
pesquisa
 
aplicada
 
incluem:
 
●  Validation  System  Core :  Otimização  de  desempenho  e  ampliação  da  cobertura  de  
testes;
 
incremento
 
na
 
flexibilidade
 
do
 
motor
 
de
 
regras
 
para
 
suportar
 
operações
 
dinâmicas
 
(adição,
 
remoção
 
e
 
atualização
 
de
 
regras)
 
e
 
melhoria
 
da
 
observabilidade
 
e
 
transparência
 
do
 
processo
 
de
 
validação
 
para
 
o
 
usuário
 
final;
 
●  Integration  Module :  Aprimoramento  da  estabilidade,  segurança  e  desempenho,  além  
do
 
aumento
 
da
 
cobertura
 
de
 
testes
 
e
 
automações,
 
tornando
 
o
 
módulo
 
mais
 
preparado
 
para
 
ambiente
 
de
 
produção;
 
e
 
●  Provisioning  Automation  Module :  Otimização  do  desempenho  do  motor  de  
provisionamento
 
e
 
ampliação
 
da
 
sua
 
cobertura
 
de
 
testes
 
automatizados,
 
visando
 
à
 
maturação
 
para
 
uso
 
em
 
produção.
 
Frente  2:  Desenvolvimento  de  Novas  Capacidades  
Esta  frente  de  trabalho  visa  expandir  a  aplicabilidade  e  a  inteligência  da  solução  por  meio  do  
desenvolvimento
 
de
 
novas
 
capacidades
 
estratégicas.
 
Neste
 
eixo,
 
serão
 
desenvolvidas
 
novas
 
funcionalidades
 
que
 
expandem
 
a
 
aplicabilidade
 
e
 
inteligência
 
da
 
solução,
 
com
 
destaque
 
para:
 
●  Suporte  a  Novos  Dispositivos:  inclusão  de  novos  tipos  de  dispositivos  críticos  de  data  
center
 
(como
 
Power
 
Max
 
e
 
HDA)
 
nos
 
pipelines
 
de
 
validação
 
e
 
provisionamento,
 
ampliando
 
o
 
escopo
 
da
 
solução;
 
●  Versioning  System :  introdução  de  controle  de  versões  para  baselines  e  padrões  de  
validação,
 
permitindo
 
rollback
,
 
ramificações
 
e
 
registro
 
histórico
 
das
 
configurações,
 
viabilizando
 
operações
 
similares
 
às
 
de
 
sistemas
 
Git
 
e
 
aprimorando
 
a
 
rastreabilidade;
 
●  Workflow-like  Automation :  integração  com  uma  plataforma  dedicada  de  automação  de  
processos
 
(como
 
o
 
N8N),
 
para
 
orquestrar
 
as
 
etapas
 
de
 
validação
 
e
 
provisionamento,
 
e
 
criar
 
uma
 
base
 
para
 
futuras
 
evoluções
 
com
 
Agentic
 
AI;
 
e
 
●  Front-End  Development :  desenvolvimento  de  uma  interface  gráfica  interativa  
(
dashboard
 
central),
 
para
 
visualização
 
de
 
status,
 
erros,
 
tarefas
 
e
 
métricas
 
de
 
saúde
 
do
 
sistema,
 
essencial
 
para
 
operação
 
em
 
ambiente
 
real.

2.3.  Problemática  Científico-Tecnológica   
A  evolução  da  automação  de  infraestrutura  em  data  centers,  impulsionada  por  paradigmas  como  
Infrastructure
 
as
 
Code
 
(IaC)
 
e
 
DevOps,
 
introduziu
 
avanços
 
significativos
 
em
 
padronização
 
e
 
rastreabilidade.
 
Contudo,
 
essa
 
evolução
 
expôs
 
simultaneamente
 
uma
 
lacuna
 
crítica:
 
a
 
ausência
 
de
 
mecanismos
 
robustos
 
para
 
garantir
 
a
 
conformidade
 
e
 
a
 
orquestração
 
de
 
processos
 
complexos
 
em
 
ambientes
 
de
 
larga
 
escala
 
e
 
heterogêneos.
 
Atualmente,  o  processo  de  validação  e  provisionamento  de  racks  em  data  centers  é  
fragmentado
 
entre
 
diversas
 
ferramentas
 
e
 
fluxos
 
manuais,
 
o
 
que
 
gera
 
inconsistências,
 
retrabalho
 
e
 
baixo
 
grau
 
de
 
auditabilidade.
 
A
 
ausência
 
de
 
um
 
sistema
 
integrado
 
que
 
consiga
 
coletar,
 
interpretar
 
e
 
aplicar
 
políticas
 
dinâmicas
 
de
 
configuração,
 
de
 
forma
 
autônoma
 
e
 
validada,
 
representa
 
um
 
gargalo
 
significativo
 
para
 
a
 
escalabilidade
 
operacional
 
dos
 
ambientes
 
de
 
data
 
center
 
corporativos.
 
Do  ponto  de  vista  científico,  o  desafio  central  está  na  construção  de  um  motor  de  validação  
automatizado
 
capaz
 
de
 
interpretar
 
regras
 
flexíveis
 
e
 
adaptativas
 
(definidas
 
em
 
YAML/JSON)
 
e
 
correlacionar
 
dados
 
oriundos
 
de
 
múltiplas
 
fontes
 
—
 
como
 
BOM
 
(
Bill
 
of
 
Materials
),
 
Asset
 
Tags
,
 
bases
 
CIS,
 
firmwares
 
e
 
serviços
 
OME
 
e
 
iDRAC
 
—
 
aplicando
 
verificações
 
inteligentes
 
e
 
independentes
 
do
 
contexto
 
físico
 
da
 
infraestrutura.
 
Isso
 
exige
 
pesquisa
 
aplicada
 
em
 
engenharia
 
de
 
software,
 
integração
 
de
 
APIs
 
e
 
sistemas
 
distribuídos,
 
além
 
de
 
uma
 
abordagem
 
científica
 
para
 
definir
 
critérios
 
de
 
consistência,
 
tolerância
 
a
 
falhas
 
e
 
desempenho.
 
A  este  desafio  de  validação,  acopla-se  a  necessidade  de  mecanismos  de  provisionamento  
autônomo
 
que
 
atuem
 
em
 
sincronia
 
com
 
as
 
validações.
 
A
 
pesquisa
 
não
 
se
 
limita
 
ao
 
uso
 
de
 
APIs
 
(e.g.,
 
Redfish),
 
mas
 
foca
 
no
 
desenvolvimento
 
de
 
pipelines
 
de
 
automação
 
declarativa.
 
O
 
estudo
 
abrange
 
a
 
verificação
 
pós-provisionamento
 
e
 
o
 
projeto
 
de
 
estratégias
 
de
 
rollback
 
controlado,
 
garantindo
 
a
 
confiabilidade
 
e
 
a
 
atomicidade
 
da
 
configuração
 
de
 
firmwares,
 
sequências
 
de
 
boot
 
e
 
sistemas
 
operacionais.
 
Em  um  nível  de  abstração  superior,  o  projeto  investiga  o  versionamento  de  regras  e  baselines  de  
configuração.
 
A
 
hipótese
 
é
 
que,
 
ao
 
tratar
 
políticas
 
de
 
infraestrutura
 
como
 
código-fonte
 
(habilitando
 
controle
 
histórico,
 
auditoria
 
e
 
ramificações),
 
cria-se
 
um
 
paradigma
 
de
 
"policy-as-code"
 
auditável.
 
Esta
 
arquitetura
 
de
 
versionamento
 
é,
 
por
 
sua
 
vez,
 
a
 
fundação
 
para
 
uma
 
linha
 
de
 
pesquisa
 
futura
 
em
 
Agentic
 
AI,
 
onde
 
agentes
 
autônomos,
 
integrados
 
a
 
plataformas
 
de
 
workflow
 
(e.g.,
 
N8N),
 
poderão
 
tomar
 
decisões
 
operacionais
 
baseadas
 
em
 
políticas,
 
logs
 
e
 
indicadores
 
do
 
sistema.
 
Por  fim,  a  criação  de  uma  interface  gráfica  interativa  agrega  um  componente  de  engenharia  
cognitiva
 
e
 
design
 
de
 
sistemas
 
complexos,
 
pois
 
envolve
 
a
 
tradução
 
visual
 
de
 
fluxos
 
técnicos
 
(validação,
 
provisionamento,
 
status
 
e
 
métricas)
 
em
 
painéis
 
compreensíveis
 
e
 
úteis
 
para
 
times
 
operacionais.
 
Essa
 
integração
 
entre
 
backend
 
automatizado,
 
versionamento
 
de
 
regras
 
e
 
front-end
 
observável
 
define
 
o
 
caráter
 
de
 
desenvolvimento
 
experimental
 
e
 
pesquisa
 
aplicada
 
deste
 
ciclo.

2.4.  Metodologia    Os  projetos  conduzidos  pelo  Departamento  de  Computação  da  Universidade  Federal  do  Ceará  
(UFC)
 
em
 
parceria
 
com
 
a
 
Dell
 
seguem
 
uma
 
metodologia
 
de
 
execução
 
padronizada,
 
desenvolvida
 
e
 
aprimorada
 
ao
 
longo
 
dos
 
últimos
 
anos
 
em
 
diversos
 
projetos
 
de
 
P&D.
 
Essa
 
metodologia
 
combina
 
práticas
 
consolidadas
 
de
 
métodos
 
ágeis,
 
aplicadas
 
a
 
equipes
 
de
 
desenvolvimento
 
distribuídas,
 
com
 
ações
 
de
 
pesquisa
 
aplicada
 
conduzidas
 
por
 
pesquisadores
 
da
 
universidade.
 
O
 
resultado
 
é
 
um
 
modelo
 
híbrido
 
de
 
trabalho
 
que
 
privilegia
 
ciclos
 
curtos
 
de
 
desenvolvimento,
 
entregas
 
incrementais
 
e
 
acompanhamento
 
contínuo
 
da
 
evolução
 
técnica
 
e
 
científica
 
das
 
soluções.
  O  processo  inicia-se  com  reuniões  de  levantamento  e  análise  de  requisitos,  nas  quais  a  equipe  
de
 
pesquisa
 
e
 
desenvolvimento
 
da
 
UFC
 
interage
 
com
 
o
 
time
 
da
 
Dell
 
responsável
 
pelo
 
projeto
 
para
 
compreender
 
detalhadamente
 
as
 
necessidades
 
do
 
sistema,
 
os
 
objetivos
 
de
 
automação
 
e
 
as
 
integrações
 
externas
 
desejadas.
 
Essa
 
fase
 
inicial
 
busca
 
mapear
 
o
 
ecossistema
 
de
 
ferramentas
 
envolvidas
 
e
 
documentar
 
os
 
fluxos
 
e
 
protocolos
 
de
 
comunicação
 
existentes,
 
fornecendo
 
insumos
 
para
 
o
 
desenho
 
técnico
 
da
 
solução.
 
A  metodologia  proposta  para  este  projeto  abrange  quatro  fases,  estruturadas  de  forma  integrada  
para
 
garantir
 
a
 
coerência
 
entre
 
o
 
diagnóstico
 
inicial
 
e
 
o
 
desenvolvimento
 
técnico.
 
Inicialmente,
 
na
 
fase
 
1
 
(Estudo
 
e
 
Entendimento
 
do
 
Problema),
 
realiza-se
 
uma
 
análise
 
do
 
domínio
 
da
 
aplicação
 
e
 
dos
 
requisitos
 
técnicos
 
e
 
funcionais,
 
mapeando
 
gargalos,
 
dependências
 
e
 
metas
 
de
 
desempenho.
 
Em
 
seguida,
 
na
 
fase
 
2
 
(Pesquisa
 
e
 
Implementação)
 
são
 
conduzidas
 
pesquisas
 
aplicadas
 
voltadas
 
à
 
experimentação
 
de
 
tecnologias,
 
frameworks
 
e
 
padrões
 
de
 
arquitetura
 
adequados
 
para
 
a
 
implementação
 
de
 
automatização
 
de
 
IaC
 
e
 
Agentic
 
AI,
 
com
 
prototipagem
 
incremental
 
e
 
validação
 
contínua
 
dos
 
resultados.
 
Essa
 
abordagem
 
permite
 
consolidar
 
um
 
modelo
 
conceitual
 
e
 
técnico
 
que
 
orienta
 
a
 
evolução
 
dos
 
módulos
 
estruturais
 
(Frente
 
1)
 
e
 
define
 
parâmetros
 
para
 
a
 
introdução
 
de
 
novas
 
funcionalidades
 
(Frente
 
2),
 
garantindo
 
alinhamento
 
entre
 
teoria,
 
experimentação
 
e
 
prática.
 
Na  sequência,  as  fases  3  (Modelagem  da  Solução)  e  4  (Desenvolvimento  e  Transferência  de  
Tecnologia)
 
visam
 
transformar
 
os
 
resultados
 
de
 
pesquisa
 
das
 
etapas
 
anteriores
 
em
 
entregas
 
robustas
 
de
 
artefatos
 
de
 
software
 
adequados
 
ao
 
ambiente
 
de
 
produção.
 
O
 
desenvolvimento
 
dos
 
módulos
 
será
 
feito
 
com
 
a
 
adoção
 
de
 
metodologias
 
ágeis,
 
integração
 
e
 
entrega
 
contínuas
 
(CI/CD)
 
e
 
ênfase
 
em
 
testes
 
automatizados,
 
permitindo
 
maturar
 
os
 
módulos
 
estruturais
 
e
 
introduzir
 
gradualmente
 
as
 
novas
 
funcionalidades
 
da
 
solução.
 
A
 
transferência
 
de
 
tecnologia
 
será
 
conduzida
 
por
 
meio
 
de
 
documentação
 
técnica,
 
treinamentos
 
e
 
sessões
 
de
 
demonstração
 
com
 
equipes
 
operacionais,
 
promovendo
 
a
 
adoção
 
efetiva
 
do
 
sistema
 
e
 
a
 
disseminação
 
do
 
conhecimento.
 
Assim,
 
a
 
metodologia
 
assegura
 
que
 
tanto
 
a
 
Frente
 
1
 
quanto
 
a
 
Frente
 
2
 
avancem
 
de
 
forma
 
coordenada,
 
combinando
 
rigor
 
científico,
 
inovação
 
tecnológica
 
e
 
aplicabilidade
 
prática.
 
O  monitoramento  do  projeto  é  conduzido  de  forma  sistemática  pelo  coordenador  e  pelo  gerente  
de
 
projeto,
 
garantindo
 
o
 
cumprimento
 
do
 
cronograma
 
e
 
do
 
orçamento
 
e
 
assegurando
 
que
 
as
 
entregas
 
mantenham
 
valor
 
técnico
 
e
 
alinhamento
 
com
 
os
 
objetivos
 
estratégicos
 
da
 
Dell.
  Entre  as  principais  características  da  metodologia  empregada  —  derivadas  dos  princípios  ágeis  
e
 
validadas
 
em
 
projetos
 
anteriores
 
—
 
destacam-se:
 ●  Inovação  contínua,  com  entregas  incrementais  que  agregam  novas  funcionalidades  e  
melhorias
 
ao
 
produto
 
em
 
cada
 
ciclo
 
de
 
iteração;

●  Coleta  de  requisitos  centrada  em  personas  e  histórias  de  usuário,  facilitando  a  
comunicação
 
entre
 
o
 
cliente
 
e
 
a
 
equipe
 
técnica
 
e
 
assegurando
 
o
 
entendimento
 
claro
 
do
 
problema
 
a
 
ser
 
resolvido;
 ●  Ciclos  curtos  de  entrega,  permitindo  validar  resultados  parciais  rapidamente  e  gerar  valor  
de
 
forma
 
contínua;
 
e
 ●  Participação  ativa  do  cliente,  com  presença  constante  do  Product  Owner  (PO)  e  ciclos  
regulares
 
de
 
feedback
 
entre
 
o
 
time
 
da
 
Dell
 
e
 
a
 
equipe
 
da
 
UFC,
 
garantindo
 
aderência
 
aos
 
requisitos
 
e
 
correção
 
de
 
rumos
 
durante
 
a
 
execução.
  Por  fim,  estão  previstas  reuniões  periódicas  de  revisão  e  acompanhamento,  nas  quais  a  equipe  
apresentará
 
o
 
progresso,
 
as
 
entregas
 
concluídas
 
e
 
os
 
indicadores
 
de
 
execução
 
à
 
Dell.
 
Essas
 
revisões
 
permitem
 
ajustes
 
dinâmicos
 
no
 
escopo,
 
redistribuição
 
de
 
esforços
 
e
 
priorização
 
de
 
atividades,
 
mantendo
 
o
 
projeto
 
alinhado
 
às
 
metas
 
técnicas
 
e
 
aos
 
resultados
 
esperados
 
para
 
o
 
ciclo
 
FY27.
  
2.5.  Estrutura  de  Etapas  com  Cronograma  e  Atividades  Planejadas    Fase  1:  Estudo  e  Entendimento  do  Problema   Etapa  1.1:  Estudo  de  Problemas  e  Limitações  de  Validação   Nesta  etapa,  serão  conduzidos  estudos  sobre  o  processo  atual  de  validação,  integração  e  
provisionamento
 
da
 
infraestrutura
 
de
 
data
 
centers
,
 
com
 
foco
 
na
 
identificação
 
das
 
limitações
 
técnicas
 
observadas
 
nos
 
módulos
 
existentes
 
do
 
sistema
 
Rack
 
Build.
 
A
 
equipe
 
analisará
 
o
 
desempenho
 
dos
 
mecanismos
 
de
 
validação,
 
as
 
restrições
 
de
 
segurança,
 
a
 
cobertura
 
de
 
testes
 
e
 
o
 
comportamento
 
das
 
integrações
 
entre
 
sistemas
 
corporativos,
 
como
 
PostgreSQL,
 
CIS
 
Database,
 
Dell
 
iDRAC
 
e
 
OpenManage
 
Enterprise
 
(OME).
 
Serão
 
também
 
revisados
 
os
 
formatos
 
e
 
fluxos
 
de
 
dados
 
utilizados
 
nos
 
processos
 
de
 
implantação
 
e
 
provisionamento,
 
com
 
o
 
objetivo
 
de
 
mapear
 
pontos
 
de
 
falha,
 
dependências
 
críticas
 
e
 
oportunidades
 
de
 
otimização.
 
Paralelamente,
 
serão
 
avaliadas
 
abordagens
 
emergentes
 
de
 
automação
 
de
 
infraestrutura
 
e
 
versionamento
 
de
 
baselines
,
 
de
 
modo
 
a
 
subsidiar
 
a
 
definição
 
das
 
melhorias
 
que
 
serão
 
incorporadas
 
nos
 
módulos
 
durante
 
o
 
novo
 
ciclo.
 Duração  prevista:  03/2026  –  04/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
Gerente
 
de
 
Projetos,
  Desenvolvedor  
Front-end,  (2x)  Desenvolvedor  Back-end.   Etapa  1.2:  Estudo  de  Estabilidade,  Segurança  e  Desempenho  de  Integrações   Nesta  etapa  inicial,  serão  conduzidos  estudos  com  o  intuito  de   investigar  e  validar  os  
mecanismos
 
técnicos
 
que
 
asseguram
 
a
 
comunicação
 
eficiente,
 
resiliente
 
e
 
protegida
 
entre
 
os
 
diversos
 
componentes
 
envolvidos
 
no
 
sistema.
 
A
 
pesquisa
 
inclui
 
a
 
análise
 
de
 
arquiteturas
 
de
 
integração,
 
padrões
 
de
 
interoperabilidade,
 
latência,
 
throughput
,
 
consumo
 
de
 
recursos
 
e
 
tolerância
 
a
 
falhas;
 
além
 
do
 
estudo
 
de
 
estratégias
 
para
 
aumentar
 
a
 
cobertura
 
de
 
testes
 
e
 
automações,
 
de
 
modo
 
a
 
deixar
 
o
 
sistema
 
mais
 
preparado
 
para
 
o
 
ambiente
 
de
 
produção.
 Duração  prevista:  03/2026  –  05/2026

Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(4x)
 Desenvolvedor  Back-end  Júnior,  
Gerente
 
de
 
Projetos,
  Desenvolvedor  Front-end,  (2x)  Desenvolvedor  Back-end.  Etapa  1.3:  Estudo  de  Provisionamento  de  Novos  Dispositivos  Nesta  etapa,  serão  realizadas  reuniões  com  a  equipe  da  Dell  e  conduzidos  estudos  sobre  
dispositivos
 
identificados
 
no
 
ecossistema
 
dos
 
datacenters,
 
os
 
quais
 
devem
 
ser
 
considerados
 
no
 
provisionamento,
 
mas
 
que
 
não
 
foram
 
contemplados
 
no
 
primeiro
 
ano
 
de
 
projeto
 
(e.g.,
 
PowerMax
 
e
 
HDA).
 Duração  prevista:  03/2026  –  05/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(4x)
 Desenvolvedor  Back-end  Júnior,  
Gerente
 
de
 
Projetos,
  Desenvolvedor  Front-end,  (2x)  Desenvolvedor  Back-end   Fase  2:  Pesquisa  e  Implementação   Etapa  2.1:  Revisão  da  Literatura  e  Visão  Geral  do  Estado  da  Arte  sobre  Agentic  AI  e  
Automação
 
para
 
IaC
 Em  paralelo  à  consolidação  do  diagnóstico  inicial  (estudo  e  entendimento  do  problema),  esta  
etapa
 
se
 
concentrará
 
em
 
esforços
 
investigativos,
 
o
 
que
 
inclui
 
o
 
levantamento
 
do
 
estado
 
da
 
arte
 
e
 
da
 
prática
 
no
 
sentido
 
de
 
viabilizar
 
a
 
implementação
 
e
 
incorporação
 
na
 
solução,
 
sob
 
uma
 
perspectiva
 
de
 
IaC,
 
de
 
uma
 
abordagem
 
pautada
 
em
 
Agentic
 
AI
 
como
 
base
 
tecnológica
 
para
 
automação
 
inteligente
 
dos
 
fluxos
 
de
 
IaC
 
(e.g.,
 
criação,
 
diagnóstico
 
e
 
reparação
 
da
 
infraestrutura).
 
Isso
 
posto,
 
serão
 
explorados
 
aspectos
 
práticos
 
das
 
plataformas
 
para
 
automação
 
de
 
processos
 
(e.g.,
 
N8N)
 
para
 
traduzir
 
decisões
 
e
 
comandos
 
de
 
agentes
 
em
 
a
ções
 
efetivas
 
(chamadas
 
de
 
API
 
ou
 
scripts
),
 
transformando
 
o
 
“raciocínio”
 
da
 
IA
 
em
 
valor
 
agregado.
 
É
 
importante
 
destacar
 
que
 
o
 
material
 
produzido
 
e
 
analisado
 
será
 
adimplente
 
aos
 
guias
 
da
 
Dell.
 
Isso
 
significa
 
que,
 
por
 
exemplo,
 
os
 
modelos
 
estudados
 
serão
 
selecionados
 
da
 
lista
 
oficial
 
de
 
modelos
 
suportados
 
e
 
disponíveis
 
na
 
Dell.
 
Além
 
disso,
 
os
 
blueprints
 
e
 
diretrizes
 
recomendados
 
da
 
Dell
 
AI
 
Acceleration
 
serão
 
considerados
 
e
 
seguidos,
 
conforme
 
preconizado
 
pela
 
contratante.
 Duração  prevista:  03/2026  –  05/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(2)
 
Testador,
 
Designer,
 
(4x)
 
Desenvolvedor
 
Back-end
 
Júnior,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.  Etapa  2.2:  Concepção  de  Estratégias  de  Automação  para  Validação  e  Provisionamento  Esta  etapa  foca  na  identificação  e  criação  de  métodos  e  estratégias  que  possibilitem  a  execução,  
de
 
forma
 
automática
 
e
 
controlada,
 
dos
 
processos
 
de
 
teste,
 
verificação
 
e
 
configuração
 
inicial
 
de
 
novos
 
componentes
 
e
 
dispositivos
 
do
 
rack.
 
O
 
estudo
 
inclui
 
a
 
definição
 
de
 
pipelines
 
de
 
integração
 
e
 
entrega
 
contínuas
 
(CI/CD),
 
criação
 
de
 
scripts
 
e
 
rotinas
 
inteligentes
 
de
 
provisionamento,
 
além
 
da
 
implementação
 
de
 
mecanismos
 
de
 
diagnóstico
 
e
 
validação
 
autônomos,
 
que
 
garantam
 
conformidade
 
com
 
requisitos
 
funcionais
 
e
 
de
 
segurança.
 
Com
 
isso,
 
busca-se
 
reduzir
 
erros
 
operacionais,
 
minimizar
 
retrabalho
 
e
 
acelerar
 
a
 
disponibilização
 
de
 
recursos
 
no
 
ambiente
 
de
 
produção,
 
promovendo
 
um
 
fluxo
 
mais
 
eficiente
 
e
 
confiável
 
em
 
todas
 
as
 
etapas
 
de
 
implantação.
 Duração  prevista:  03/2026  –  07/2026

Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(2x)
 
Testador,
 
(4x)
 
Desenvolvedor
 
Back-end
 
Júnior,
 
Gerente
 
de
 
Projetos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.
   Etapa  2.3:  Implementação  e  Avaliação  das  Estratégias  de  Automação  Após  a  análise  do  estado  da  arte  e  identificação  das  ferramentas  e  frameworks  que  mais  se  
adequem
 
à
 
implementação
 
de
 
automação
 
para
 
IaC
 
e
 
possibilitem
 
o
 
uso
 
de
 
Agentic
 
AI
 
e
 
modelos
 
de
 
ML
 
no
 
ambiente
 
da
 
Dell,
 
nesta
 
etapa,
 
iremos
 
implementar
 
e
 
avaliar
 
diferentes
 
estratégias
 
e
 
arquiteturas
 
de
 
automação
 
e
 
agentes
 
para
 
auxiliar
 
nos
 
processos
 
desenvolvidos
 
no
 
primeiro
 
ano
 
do
 
projeto.
 Duração  prevista:  06/2026  –  09/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(2x)
 
Testador,
 
Designer,
 
(4x)
 
Desenvolvedor
 
Back-end
 
Júnior,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.
   Etapa  2.4:  Pesquisa  Aplicada  em  Otimizações  de  Sistemas  O  objetivo  desta  etapa  é  investigar  e  aplicar  otimização  de  sistemas  para  endereçar  a  latência  e  
a
 
escalabilidade
 
do
 
pipeline
 
de
 
validação
 
e
 
provisionamento
 
de
 
IaC.
 
A
 
pesquisa
 
visa
 
reduzir
 
o
 
tempo
 
total
 
de
 
deploy
 
(latência)
 
e
 
aumentar
 
a
 
capacidade
 
de
 
processamento
 
concorrente
 
(vazão
 
ou
 
throughput)
 
do
 
sistema.
 
A
 
investigação
 
se
 
concentrará
 
em
 
modelos
 
de
 
execução
 
paralela
 
e
 
orquestração
 
inteligente
 
de
 
recursos.
 
O
 
primeiro
 
domínio
 
envolve
 
a
 
análise
 
e
 
experimentação
 
de
 
técnicas
 
de
 
paralelização
 
(nível
 
de
 
tarefa
 
e
 
dados)
 
para
 
converter
 
processos
 
sequenciais,
 
como
 
validações
 
de
 
racks,
 
em
 
fluxos
 
de
 
execução
 
concorrentes.
 
O
 
segundo
 
abrange
 
o
 
estudo
 
de
 
heurísticas
 
para
 
a
 
orquestração
 
de
 
tarefas,
 
focando
 
em
 
otimizar
 
a
 
alocação
 
de
 
recursos
 
e
 
gerenciar
 
eficientemente
 
as
 
dependências
 
entre
 
tarefas
 
para
 
minimizar
 
a
 
ociosidade.
 
 Duração  prevista:  05/2026  –  01/2027  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(2x)
 
Testador,
 
Designer,
 
(4x)
 
Desenvolvedor
 
Back-end
 
Júnior,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.
  Fase   3:  Modelagem  da  Solução   Etapa  3.1:  Atualização  da  Arquitetura  da  Solução  Nesta  fase,  a  arquitetura  do  sistema  será  (re)modelada,  considerando  o  aprimoramento  dos  
módulos
 
e
 
as
 
novas
 
funcionalidades
 
planejadas.
 
A
 
atividade
 
incluirá
 
a
 
atualização
 
da
 
arquitetura
 
de
 
dados,
 
fluxos
 
de
 
comunicação
 
entre
 
componentes,
 
estratégias
 
de
 
versionamento
 
e
 
estruturas
 
de
 
logging
 
e
 
observabilidade.
 
 Duração  prevista:  04/2026  –  06/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(4x)Desenvolvedor
 
Back-end
 
Júnior,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.

Etapa  3.2:  Modelagem  do  Módulo  de  Validação  Nesta  fase,  será  elaborado  o  novo  desenho  do  módulo  de  validação,  com  a  eventual  adaptação  
do
 
formato
 
da
 
arquitetura
 
criada
 
no
 
primeiro
 
ano
 
de
 
projeto
 
à
 
ferramenta
 
de
 
automação
 
escolhida
 
para
 
implementar
 
o
 
workflow
 
inteligente.
 
Aqui
 
os
 
detalhes
 
da
 
automação
 
serão
 
definidos
 
para
 
que
 
o
 
processo
 
ocorra
 
de
 
maneira
 
confiável,
 
segura
 
e
 
passível
 
de
 
ser
 
auditado.
 Duração  prevista:  04/2026  –  06/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.
   Etapa  3.3:  Modelagem  do  Módulo  de  Integração  e  Provisionamento  Nesta  fase,  o  módulo  de  Integração  e  Provisionamento  será  remodelado  para  contemplar  os  
aperfeiçoamentos
 
do
 
novo
 
ciclo
 
do
 
projeto.
 
Os
 
detalhes
 
das
 
integrações
 
já
 
implementadas
 
no
 
primeiro
 
ano
 
de
 
projeto
 
e
 
possíveis
 
novas
 
integrações
 
que
 
venham
 
a
 
ser
 
elencadas
 
serão
 
identificados,
 
assim
 
como
 
todo
 
o
 
processo
 
de
 
provisionamento
 
já
 
posto
 
em
 
prática
 
para
 
servidores.
 
Os
 
novos
 
hardwares
 
identificados
 
no
 
ecossistema
 
dos
 
datacenters
 
Dell,
 
como
 
PowerMax
 
e
 
HDA,
  
também
 
serão
 
adicionados
 
ao
 
workflow
 
de
 
automação.
 
 Duração  prevista:  04/2026  –  06/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
Designer,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end,  Etapa  3.4:  Modelagem  das  Interfaces  de  UI/UX  Nesta  fase,  serão  estudadas  as  abordagens  de  experiência  do  usuário  (UX)  para  projetar  a  
interface
 
da
 
aplicação.
 
Serão
 
criados
 
e
 
refinados
 
protótipos
 
de
 
alta
 
fidelidade
 
para
 
aprovação
 
da
 
equipe
 
da
 
Dell,
 
garantindo
 
uma
 
UX
 
intuitiva
 
e
 
responsiva
 
para
 
os
 
processos
 
de
 
coleta
 
de
 
dados
 
e
 
aprovação.
 
Esses
 
designs
 
serão
 
baseados
 
nas
 
necessidades
 
dos
 
usuários,
 
nos
 
requisitos
 
da
 
aplicação
 
e
 
no
 
Dell
 
Design
 
System
 
(DDS).
 
Além
 
disso,
 
será
 
definida
 
a
 
seleção
 
das
 
tecnologias
 
de
 
desenvolvimento
 
a
 
serem
 
utilizadas.
 Duração  prevista:  03/2026  –  06/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
Designer,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos.
  Fase  4:  Desenvolvimento  e  Transferência  de  Tecnologia   Etapa  4.1:  Implementação  de  Melhorias  e  Avaliação  de  Módulos  Existentes  Esta  etapa  abrangerá  a  implementação  dos  aperfeiçoamentos  dos  módulos  e  funcionalidades  
definidas
 
nas
 
fases
 
anteriores,
 
garantindo
 
a
 
integração
 
entre
 
os
 
componentes
 
e
 
a
 
operacionalização
 
da
 
solução
 
em
 
ambiente
 
de
 
produção.
 
Serão
 
conduzidos
 
testes
 
unitários,
 
de
 
integração,
 
de
 
desempenho,
 
assegurando
 
conformidade
 
com
 
padrões
 
de
 
qualidade
 
e
 
segurança
 
da
 
Dell.
 
Duração
 
prevista:
 
05/2026
 
–
 
11/2026
 Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software
 
(PhD),
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(2x)
 
Testador,
 
Designer,
 
(4x)

Desenvolvedor  Back-end  Júnior,  Gerente  de  Projetos,  Analista  de  Requisitos,  Desenvolvedor  
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.  Etapa  4.2:  Desenvolvimento  de  Novas  Funcionalidades  Uma  vez  definida  a  nova  arquitetura  do  sistema,  conduzidos  os  estudos  das  etapas  anteriores  e  
modelados
 
os
 
módulos
 
para
 
atender
 
às
 
novas
 
funcionalidades,
 
iremos
 
iniciar
 
a
 
implementação
 
da
 
automação,
 
a
 
integração
 
de
 
novos
 
dispositivos,
 
versionamento,
 
e
 
as
 
interfaces
 
de
 
usuários
 
do
 
sistema.
 
A
 
equipe
 
irá
 
seguir
 
as
 
boas
 
práticas
 
de
 
desenvolvimento
 
e
 
implementará
 
em
 
paralelo
 
os
 
testes
 
unitários.
 Duração  prevista:  07/2026  –  12/2026  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(2x)
 
Testador,
 
Designer,
 
(4x)
 
Desenvolvedor
 
Back-end
 
Júnior,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.  Etapa  4.3:  Implantação  e  Testes  Contínuos  de  Soluções  Esta  etapa  contempla  a  execução  dos  testes  unitários  e  de  integração,  que  serão  realizados  
concorrentemente
 
ao
 
desenvolvimento,
 
para
 
validar
 
a
 
funcionalidade
 
e
 
confiabilidade
 
dos
 
endpoints
 
da
 
API.
 
Esses
 
testes
 
garantirão
 
que
 
cada
 
módulo
 
opere
 
conforme
 
o
 
esperado
 
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
 
monitorará
 
esses
 
testes
 
e
 
validará
 
os
 
resultados
 
como
 
aprovados
 
ou
 
não.
 
Como
 
todos
 
os
 
módulos
 
operarão
 
no
 
ecossistema
 
Dell,
 
aderiremos
 
aos
 
padrões
 
de
 
segurança
 
e
 
conformidade
 
da
 
Dell.
 
 Duração  prevista:  07/2026  –  02/2027  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(2x)
 
Testador,
 
Designer,
 
(4x)
 
Desenvolvedor
 
Back-end
 
Júnior,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.  Etapa  4.4:  Transferência  Contínua  de  Conhecimento  Esta  etapa  abrangerá  atualizações  de  progresso  e  compartilhamento  de  conhecimento  com  a  
equipe
 
da
 
Dell,
 
além
 
de
 
manter
 
a
 
documentação
 
do
 
projeto
 
consistentemente
 
atualizada
 
durante
 
o
 
desenvolvimento.
 
Manuais
 
do
 
usuário
 
e
 
guias
 
da
 
solução
 
serão
 
documentados
 
e
 
mantidos
 
no
 
Confluence,
 
garantindo
 
fácil
 
acesso
 
e
 
referência
 
para
 
a
 
equipe
 
da
 
Dell.
 Duração  prevista:  06/2026  –  02/2027  Participantes:  Coordenador  do  Projeto,  Pesquisador  em  Engenharia  de  Software,  Pesquisador  
em
 
Integração
 
de
 
Sistemas,
 
Especialista
 
em
 
Integração
 
de
 
Sistemas,
 
Consultor
 
em
 
Arquitetura
 
de
 
Software,
 
Especialista
 
em
 
Engenharia
 
de
 
Software,
 
(2x)
 
Testador,
 
Designer,
 
(4x)
 
Desenvolvedor
 
Back-end
 
Júnior,
 
Gerente
 
de
 
Projetos,
 
Analista
 
de
 
Requisitos,
 
Desenvolvedor
 
Front-end,
 
(2x)
 
Desenvolvedor
 
Back-end.
   
2.6.  Duração   
Data  de  início:  01/03/2026  Data  de  estimada  de  término:  28/02/2027    
2.7.  Resultados  Esperados

O  MVP  (Mínimo  Produto  Viável)  deste  ciclo  do  projeto  entregará  uma  versão  amadurecida  e  
ampliada
 
do
 
sistema
 
Rack
 
Build,
 
pronta
 
para
 
operação
 
em
 
ambiente
 
produtivo.
 
Entre
 
os
 
resultados
 
previstos
 
estão:
 ●  Módulos  aprimorados  de  Validação,  Integração  e  Provisionamento  com  desempenho  e  
estabilidade
 
otimizados;
 ●  Suporte  ampliado  a  novos  dispositivos  (Power  Max,  HDA);  ●  Sistema  de  versionamento  de  baselines  e  histórico  de  validações;  ●  Integração  de  workflows  automatizados  para  orquestração  completa;  ●  Interface  gráfica  com  dashboard  interativo;  ●  Documentação  atualizada  e  transferência  tecnológica  à  equipe  Dell;  ●  1  nova  publicação  científica  e  1  protótipo/processo/software  registrado.    2.8.  Indicadores  de  Resultados  Esperados  (§  2º,  art.  24,  Decreto  nº  5.906/2006)
  
1.  Patentes  depositadas  no  Brasil  e  no  exterior   Quantas  patentes  se  espera  gerar?  Número  de  patentes  
☐  
2.  Concessão  de  co-titularidade  ou  de  participação  nos  resultados  da  pesquisa  e  desenvolvimento  às  instituições  convenentes  
☐  
3.  Protótipos,  processos,  softwares  e  produtos  que  incorporem  inovação  científica  ou  tecnológica   
Espera-se  gerar  1  software.  
x  
4.  Publicações  científicas  e  tecnológicas  em  periódicos  ou  eventos  científicos  com  revisão  pelos  pares.   Quantas  publicações  se  espera  gerar?  Espera-se  gerar  1  publicação.  
x  
5.  Dissertações  e  teses  defendidas.   ☐   
3.  Dos  Recursos  Necessários  ao  Desenvolvimento  do  Projeto    3.1  Introdução    Os  recursos  para  o  projeto  “ Rack  Infrastructure  Deployment  Validation  and  Provisioning  II ”  
foram
 
estimados
 
com
 
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
 
direto
 
e
 
indireto
 
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
  3.2  Recursos  Humanos  Diretos  (Decreto  nº  5.906/2006,  art.  25,  inciso  III)   Função:  Coordenador  do  Projeto  Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  pela  
coordenação
 
científica
 
e
 
técnica
 
do
 
projeto,
 
incluindo
 
a
 
definição
 
da
 
metodologia
 
e
 
dos
 
instrumentos
 
a
 
serem
 
utilizados
 
na
 
construção
 
da
 
solução.
 
Também
 
ficará
 
encarregado

de  conduzir  as  pesquisas,  realizar  a  revisão  bibliográfica  e  acompanhar  tecnicamente  
todos
 
os
 
artefatos
 
gerados
 
durante
 
o
 
desenvolvimento
 
das
 
tecnologias
 
previstas.
 
Além
 
disso,
 
coordenará
 
a
 
publicação
 
de
 
artigos
 
e
 
a
 
orientação
 
de
 
trabalhos
 
relacionados
 
às
 
temáticas
 
abordadas
 
neste
 
projeto.
 Horas  trabalhadas:  192  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  90.000,00   Função:  Pesquisador  em  Engenharia  de  Software  Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  pela  pesquisa  
das
 
melhores
 
práticas
 
e
 
padrões
 
de
 
desenvolvimento,
 
bem
 
como
 
os
 
testes
 
necessários
 
para
 
validar
 
a
 
solução
 
desenvolvida.
 
As
 
melhores
 
práticas
 
para
 
integração
 
contínua
 
e
 
entrega
 
contínua
 
também
 
são
 
pesquisadas
 
e
 
difundidas
 
por
 
este
 
profissional.
 
Além
 
disso,
 
também
 
fazem
 
parte
 
das
 
suas
 
atividades:
 
elaboração
 
do
 
plano
 
de
 
testes,
 
elaboração
 
e
 
implementação
 
dos
 
procedimentos
 
e
 
roteiros
 
de
 
testes,
 
avaliação
 
dos
 
riscos
 
e
 
impactos
 
dos
 
testes,
 
configuração
 
do
 
ambiente
 
necessário
 
para
 
realização
 
dos
 
testes
 
automatizados
 
e
 
deploy
 
em
 
produção.
 
Finalmente,
 
este
 
profissional
 
será
 
responsável
 
pelo
 
planejamento
 
dos
 
testes
 
de
 
desempenho
 
visando
 
otimizar
 
serviços
 
e
 
melhorar
 
o
 
desempenho
 
da
 
solução,
 
além
 
de
 
supervisionar
 
alunos
 
de
 
pós-graduação
 
e
 
graduação.
 
  Horas  trabalhadas:  192  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  66.000,00   Função:  Pesquisador  em  Integração  de  Sistemas   Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  pelo  
mapeamento
 
de
 
integrações
 
externas
 
da
 
solução
 
e
 
estudo
 
das
 
interfaces
 
existentes.
 
É
 
responsável
 
por
 
conduzir
 
as
 
pesquisas
 
que
 
levarão
 
à
 
escolha
 
das
 
estratégias
 
necessárias
 
para
 
integração
 
de
 
componentes
 
na
 
aplicação,
 
bem
 
como
 
na
 
definição
 
de
 
soluções
 
para
 
o
 
projeto
 
da
 
arquitetura,
 
de
 
modo
 
a
 
atender
 
os
 
requisitos
 
da
 
solução.
 
Suas
 
atividades
 
também
 
envolvem
 
estudar
 
como
 
otimizar
 
eventuais
 
consultas
 
a
 
banco
 
de
 
dados,
 
além
 
de
 
colaborar
 
no
 
design
 
e
 
implementação
 
de
 
esquemas
 
de
 
dados
 
que
 
suportem
 
os
 
objetivos
 
da
 
pesquisa.
 
Este
 
profissional
 
atuará
 
como
 
consultor
 
científico,
 
em
 
constante
 
conversa
 
com
 
a
 
equipe
 
de
 
engenharia
 
de
 
software
 
e
 
outros
 
líderes
 
de
 
pesquisa,
 
além
 
de
 
supervisionar
 
alunos
 
de
 
pós-graduação
 
e
 
graduação.
 
  Horas  trabalhadas:  192  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  66.000,00   
Função:
 
Especialista
 
em
 
Integração
 
de
 
Sistemas
 
 Formação:  Superior  com  Mestrado,  Mestrando  ou  Doutorando  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027   Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  pelo  
mapeamento
 
das
 
integrações
 
externas
 
da
 
solução
 
e
 
pelo
 
estudo
 
das
 
interfaces
 
existentes.
 
Além
 
disso,
 
conduzirá
 
pesquisas
 
para
 
definir
 
as
 
estratégias
 
necessárias
 
à
 
integração
 
de
 
componentes
 
na
 
aplicação,
 
bem
 
como
 
para
 
a
 
definição
 
de
 
soluções
 
no
 
projeto
 
da
 
arquitetura,
 
garantindo
 
o
 
atendimento
 
aos
 
requisitos
 
da
 
solução.
 
Este
 
profissional
 
será
 
liderado
 
pelo
 
Pesquisador
 
em
 
Integração
 
de
 
Sistemas
 
e
 
acompanhará
 
as
 
atividades
 
dos
 
alunos
 
de
 
graduação.
 Horas  trabalhadas:  960  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  38.400,00

Função:
 
Consultor
 
em
 
Arquitetura
 
de
 
Software
 
 Formação:  Superior  com  Doutorado  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  por  definir  
diretrizes
 
e
 
estratégias
 
para
 
o
 
desenvolvimento
 
da
 
arquitetura
 
da
 
solução,
 
garantindo
 
alinhamento
 
com
 
as
 
melhores
 
práticas
 
e
 
padrões
 
do
 
setor.
 
Ele
 
atuará
 
na
 
avaliação
 
e
 
seleção
 
de
 
tecnologias,
 
frameworks
 
e
 
metodologias
 
adequadas
 
ao
 
projeto,
 
além
 
de
 
orientar
 
a
 
equipe
 
técnica
 
na
 
implementação
 
das
 
soluções
 
arquiteturais.
 Horas  trabalhadas:  192  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  48.000,00   
Função:
 
Especialista
 
em
 
Engenharia
 
de
 
Software
 
 Formação:  Superior  com  Mestrado,  Mestrando  ou  Doutorando  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  atuará  na  pesquisa  das  melhores  
práticas
 
e
 
padrões
 
de
 
desenvolvimento,
 
bem
 
como
 
os
 
testes
 
necessários
 
para
 
validar
 
a
 
solução
 
desenvolvida.
 
As
 
melhores
 
práticas
 
para
 
integração
 
contínua
 
e
 
entrega
 
contínua
 
também
 
são
 
pesquisadas
 
e
 
difundidas
 
por
 
este
 
profissional.
 
O
 
profissional
 
será
 
liderado
 
pelo
 
Pesquisador
 
em
 
Engenharia
 
de
 
Software
 
e
 
atuará
 
na
 
elaboração
 
do
 
plano
 
de
 
testes,
 
elaboração
 
e
 
implementação
 
dos
 
procedimentos
 
e
 
roteiros
 
de
 
testes,
 
avaliação
 
dos
 
riscos
 
e
 
impactos
 
dos
 
testes,
 
configuração
 
do
 
ambiente
 
necessário
 
para
 
realização
 
dos
 
testes
 
automatizados.
 
 Horas  trabalhadas:  960  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$   38.400,00        Função:  Testador  1  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  atuará  na  implementação  e  
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
 
O
 
profissional
 
será
 
liderado
 
pelo
 
Pesquisador
 
em
 
Engenharia
 
de
 
Software
 
e
 
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
 
código,
 
como
 
Sonarqube,
 
Snyk
 
e
 
JFrog
 
Xray,
 
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
 Horas  trabalhadas:  1.200  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Testador  2  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  atuará  na  implementação  e  
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
 
O
 
profissional
 
será
 
liderado
 
pelo
 
Pesquisador
 
em
 
Engenharia
 
de
 
Software
 
e
 
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
 
código,
 
como
 
Sonarqube,
 
Snyk
 
e
 
JFrog
 
Xray,
 
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
 Horas  trabalhadas:  1.200  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00

Função:  Desenvolvedor  Back-end  Júnior  1  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  atuará  no  desenvolvimento  dos  
módulos
 
e
 
funcionalidades
 
do
 
backend
 
da
 
solução.
 
Além
 
disso,
 
deve
 
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
 Horas  trabalhadas:  1.200  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Desenvolvedor  Back-end  Júnior  2  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  atuará  no  desenvolvimento  dos  
módulos
 
e
 
funcionalidades
 
do
 
backend
 
da
 
solução.
 
Além
 
disso,
 
deve
 
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
 Horas  trabalhadas:  1.200  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Desenvolvedor  Back-end  Júnior  3  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  atuará  no  desenvolvimento  dos  
módulos
 
e
 
funcionalidades
 
do
 
backend
 
da
 
solução.
 
Além
 
disso,
 
deve
 
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
 Horas  trabalhadas:  1.200  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Desenvolvedor  Back-end  Júnior  4  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  atuará  no  desenvolvimento  dos  
módulos
 
e
 
funcionalidades
 
do
 
backend
 
da
 
solução.
 
Além
 
disso,
 
deve
 
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
 Horas  trabalhadas:  1.200  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$   16.800,00   Função:  Designer  Formação:  Médio  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  Responsável  pelas  atividades  relacionadas  a  
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

engenharia  de  software  no  desenvolvimento  do  front-end  do  projeto.  Também  fará  
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
 Horas  trabalhadas:  1.200h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  16.800,00   Função:  Gerente  de  Projetos  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  pela  realização  
das
 
atividades
 
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
 Horas  trabalhadas:  480  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  83.388,35    Função:  Analista  de  Requisitos  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  pela  realização  
das
 
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
 
requisitos
 
da
 
solução.
 
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
 
das
 
sprints
.
 
O
 
profissional
 
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
 
entregas
 Horas  trabalhadas:  1920  h  
Total
 
do
 
dispêndio
 
(remuneração
 
total
 
com
 
encargos)
:
 
R$
 
117.234,56
  Função:  Desenvolvedor  Back-end  1  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  por  desenvolver  
os
 
módulos
 
e
 
funcionalidades
 
do
 
backend
 
da
 
solução.
 
Ele
 
deve
 
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
 
fazer
 
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
 
Além
 
disso,
 
irá
 
atuar
 
no
 
desenvolvimento
 
das
 
soluções
 
e
 
nas
 
APIs
 
de
 
integração
 
com
 
demais
 
componentes
 
do
 
sistema.
 
Também
 
é
 
responsável
 
pela
 
documentação
 
do
 
backend
 
do
 
projeto
 
e
 
suportar
 
a
 
execução
 
de
 
ajustes
 
finais
 
na
 
solução
 
para
 
ser
 
possível
 
a
 
transferência
 
tecnológica
 
do
 
mesmo
 
para
 
a
 
Dell.
 Horas  trabalhadas:  1920  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  145.361,03    Função:  Desenvolvedor  Back-end  2  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  por  desenvolver

os  módulos  e  funcionalidades  do  backend  da  solução.  Ele  deve  implementar  testes  
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
 
Além
 
disso,
 
irá
 
atuar
 
no
 
desenvolvimento
 
das
 
soluções
 
e
 
nas
 
APIs
 
de
 
integração
 
com
 
demais
 
componentes
 
do
 
sistema.
 
Também
 
é
 
responsável
 
pela
 
documentação
 
do
 
backend
 
do
 
projeto
 
e
 
suportar
 
a
 
execução
 
de
 
ajustes
 
finais
 
na
 
solução
 
para
 
ser
 
possível
 
a
 
transferência
 
tecnológica
 
do
 
mesmo
 
para
 
a
 
Dell.
 Horas  trabalhadas:  1920  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  143.644,75   Função:  Desenvolvedor  Front-end  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  por  desenvolver  
os
 
módulos
 
e
 
funcionalidades
 
do
 
front
 
end
 
da
 
solução.
 
Ele
 
deve
 
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
 
Também
 
é
 
responsável
 
pela
 
documentação
 
do
 
backend
 
do
 
projeto
 
e
 
suportar
 
a
 
execução
 
de
 
ajustes
 
finais
 
na
 
solução
 
para
 
ser
 
possível
 
a
 
transferência
 
tecnológica
 
do
 
mesmo
 
para
 
a
 
Dell.
 Horas  trabalhadas:  1920  h  Total  do  dispêndio  (remuneração  total  com  encargos) :  R$  127.596,88   3.3  Recursos  Humanos  Indiretos  (Decreto  nº  5.906/2006,  art.  25,  inciso  IV)   Função:  Analista  de  Financeiro  Formação:  Superior  Data  de  Início:  01/03/2026  Data  de  Fim:  28/02/2027  Atuação  e  justificativa  para  o  projeto:  O  profissional  será  responsável  pelo  suporte  
administrativo
 
e
 
financeiro
 
na
 
execução
 
das
 
atividades
 
do
 
projeto,
 
incluindo
 
o
 
controle
 
das
 
folhas
 
de
 
ponto
 
dos
 
colaboradores,
 
a
 
gestão
 
e
 
digitalização
 
da
 
documentação
 
dos
 
mesmos,
 
a
 
organização
 
e
 
inclusão
 
dos
 
dados
 
no
 
banco
 
de
 
dados
 
dos
 
colaboradores,
 
a
 
cotação
 
e
 
solicitação
 
de
 
materiais
 
para
 
o
 
projeto,
 
o
 
apoio
 
na
 
elaboração
 
do
 
RDA
 
do
 
projeto,
 
a
 
validação
 
de
 
ofícios,
 
o
 
arquivamento
 
de
 
documentos
 
e
 
o
 
suporte
 
a
 
outras
 
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
 
R$
 
97.108,62
          
  3.4  Viagens  (Decreto  nº  5.906/2006,  art.  25,  inciso  VII)   Não  se  aplica   3.5  Serviços  Técnicos  (Decreto  nº  5.906/2006,  art.  25,  inciso  IX)   Não  se  aplica   3.6  Equipamentos  e  Software  (Decreto  nº  5.906/2006,  art.  25,  inciso  I)   Dispêndio  (Adequação):  04  Notebooks  Dell  —   Quantitativo  adequado  para  atender  às  
atividades
 
da
 
equipe
 
do
 
projeto.
 Tipo  de  Apropriação :  Equipamento  TICs  —  Aquisição  Descrição:  Notebook  Dell  -  Notebook  Máquina  dedicada  à  equipe  do  projeto  para  
realização
 
das
 
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

semelhantes:  Notebook  Dell  (Core  i7  13ª  geração,  RAM  32  GB,  SSD  1  TB,  Wi-Fi,  FHD,  
Bat.
 
6
 
Cel.).
 Valor:  R$  28.000,00  Justificativa  (Pertinência):  A  solicitação  de  novos  equipamentos  tem  como  objetivo  
reduzir
 
a
 
defasagem
 
tecnológica
 
dos
 
dispositivos
 
atualmente
 
utilizados
 
pela
 
equipe.
 
Considerando
 
que,
 
nos
 
últimos
 
anos,
 
os
 
projetos
 
aprovados
 
não
 
incluíram
 
a
 
aquisição
 
de
 
computadores
 
em
 
seus
 
planos
 
de
 
trabalho.
 
Por
 
fim,
 
como
 
em
 
qualquer
 
parque
 
tecnológico,
 
é
 
natural
 
que
 
parte
 
dos
 
equipamentos
 
apresente
 
falhas
 
cujo
 
custo
 
de
 
reparo
 
muitas
 
vezes
 
não
 
se
 
mostra
 
compensatório,
 
reforçando
 
a
 
necessidade
 
de
 
renovação
 
periódica
 
do
 
acervo.
     
  Dispêndio  (Adequação):  3  unidades-chave  de  acesso  HSK  —   Quantitativo  adequado  
em
 
relação
 
os
 
novos
 
perfis
 
do
 
projeto
 Tipo  de  Apropriação :  Equipamento  Outros  —  Aquisição  Descrição:  Equipamento  utilizado  para  a  autenticação  ao  acesso  à  rede  Dell   Valor:  R$  600,00  Justificativa  (Pertinência):  Chaves  físicas  de  acesso  à  infraestrutura  da  rede  Dell.   Dispêndio  (Adequação):  3  unidades  licenças  Google  Workspace  —   Quantitativo  
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
 Valor:  R$  2.700,00   Justificativa  (Pertinência):  Aquisição  de        licenças  Google  Workspace      ,  
necessárias
 
para
 
acesso
 
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
 
A
 
gestão
 
dos
 
projetos
 
desenvolvidos
 
no
 
ATLab/UFC
 
exige
 
que
 
documentos
 
e
 
demais
 
arquivos
 
produzidos
 
em
 
parceria
 
com
 
instituições,
 
como
 
a
 
Dell,
 
sejam
 
devidamente
 
preservados.
 
Essa
 
gestão
 
requer
 
um
 
controle
 
interno
 
e
 
independente
 
da
 
infraestrutura
 
dos
 
parceiros,
 
a
 
fim
 
de
 
garantir
 
autonomia
 
nas
 
atividades
 
e
 
assegurar
 
a
 
manutenção
 
de
 
um
 
histórico
 
abrangente
 
de
 
documentos.
 
Além
 
disso,
 
determinados
 
perfis
 
—
 
especialmente
 
os
 
gerenciais
 
—
 
necessitam
 
de
 
funcionalidades
 
específicas,
 
como
 
a
 
gravação
 
de
 
reuniões.
 
Ressalta-se
 
que
 
o
 
número
 
de
 
licenças
 
solicitadas
 
(de
 
3
 
a
 
4,
 
a
 
depender
 
da
 
cotação
 
no
 
momento
 
da
 
aquisição)
 
é
 
significativamente
 
inferior
 
ao
 
total
 
de
 
participantes
 
por
 
projeto,
 
porém
 
são
 
essenciais
 
para
 
a
 
atual
 
forma
 
de
 
gerenciamento
 
adotada
 
em
 
nosso
 
laboratório.
  3.7  Treinamento  (Decreto  nº  5.906/2006,  art.  25,  inciso  VIII)   Não  se  aplica   3.8  Livros  /  Periódicos  Técnicos  (Decreto  nº  5.906/2006,  art.  25,  inciso  V)   Não  se  aplica   3.9  Material  de  Consumo  (Decreto  nº  5.906/2006,  art.  25,  inciso  VI)   Não  se  aplica   3.10  Obra  Civil  /  Construções  (Decreto  de  nº  5.906,  de  26  de  setembro  de  2006,  art.  
25º,
 
inciso
 
Il)
  Não  se  aplica   3.11  Outros  Correlatos  (Decreto  nº  5.906/2006,  art.  25,  inciso  X)

Não  se  aplica   3.12  Custos  Incorridos  pela  instituição   Discriminação  dos  principais  dispêndios  e  destinações:  Despesas  operacionais  
incorridas
 
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
 Valor:  R$  296.857,70  Justificativa:  São  considerados  como  custos  incorridos  os  valores  descritos  a  seguir,  
conforme
 
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
 
5906/2006,
 
que
 
somam
 
(R$
 
42.397,49)
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
 
105.993,73)
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
 
52.996,87)
 
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
 
conforme
 
o
 
que
 
determina
 
a
 
legislação
 
vigente,
 
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
 
(R$
 
60.248,65)
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
  RH  Direto  RH  Indireto  Total  Nível  Superior  Médio  Superior  Médio  Quantidade  de  pessoas  11  7  1   19  Valor  (R$)  R$  964,025.57  R$  117,600.00  
R$
 
97.108,62
   
 R$  1.178,734.19  Total  de  horas  trabalhadas  10.800  8.400  1.920   21.200   Rubrica  Total  %  RH  Total  
 R$  1.178,734.19  78,22%  Obras  Civis    Serviços  Técnicos    Livros  E  Periódicos  Técnicos    Outros  Correlatos    Equipamento  e  Software  
31.300,00  2,08%  Material  De  Consumo    Treinamento    Viagens    Custo  Incorrido  (+  Fundo  de  Reserva)  
 R$  296.857,70  19,70%  TOTAL  DE  DISPÊNDIOS  
R$  1.506,891.90  100,00%  
 3.14.  Cronograma  Previsto  dos  Gastos   Descrições  
Mar./2026 Abr./2026 Mai./202 Jun./2026 Jul./2026 Ago./2026 Set./2026 Rubricas      Previsto      Previsto      Previsto       Previsto      Previsto       Previsto       Previsto RH  Direto  
9 0 . 7 7 9 , 7 6 
 
8 4 . 6 2 9 , 7 2 
 
9 8 . 9 6 7 , 8 2 
 
9 0 . 1 9 8 , 0 5 
 
8 9 . 2 3 3 , 9 0 
 
8 9 . 2 7 1 , 3 0 
 
8 9 . 6 5 6 , 6 7

RH  Indireto  
7 . 7 3 5 , 4 0 
 
7 . 1 7 7 , 2 8 
 
1 0 . 1 2 1 , 1 4 
 
8 . 2 3 7 , 2 4 
 
7 . 8 8 8 , 4 3 
 
7 . 8 9 7 , 2 3 
 
8 . 0 0 8 , 6 5 
 Equipamentos  e  software  
3 1 . 3 0 0 , 0 0 
       Material  de  consumo         Livros/periódicos  técnicos         Outros  correlatos         Custos  incorridos  pela  instituição  
3 1 . 8 4 7 , 5 5 
 
2 2 . 5 2 3 , 0 1 
 
2 6 . 7 6 2 , 7 9 
 
2 4 . 1 4 9 , 1 3 
 
2 3 . 8 2 7 , 0 2 
 
2 3 . 8 3 8 , 3 6 
 
2 3 . 9 6 0 , 2 3 
 Total  de  recursos  financeiros  (R$)  
1 6 1 . 6 6 2 , 7 1 
 
1 1 4 . 3 3 0 , 0 1 
 
1 3 5 . 8 5 1 , 7 5 
 
1 2 2 . 5 8 4 , 4 2 
 
1 2 0 . 9 4 9 , 3 6 
 
1 2 1 . 0 0 6 , 8 9 
 
1 6 1 . 6 6 2 , 7 1 
     Descrições  
Out./2026 Nov./2026 Dez./2026 Jan./2027 Fev./2027 Total  %  Rubricas       Previsto      Previsto       Previsto       Previsto       Previsto      Previsto    RH  Direto  
8 9 . 6 5 6 , 6 7 
 
9 0 . 2 6 1 , 6 7 
 
8 9 . 6 5 6 , 6 7 
 
8 9 . 6 5 6 , 6 7 
 
8 9 . 6 5 6 , 6 7 
 
1 . 0 8 1 . 6 2 5 , 5 7 
 
7 1 , 7 8 % 
 RH  Indireto  
8 . 0 0 8 , 6 5 
 
8 . 0 0 8 , 6 5 
 
8 . 0 0 8 , 6 5 
 
8 . 0 0 8 , 6 5 
 
8 . 0 0 8 , 6 5 
 
9 7 . 1 0 8 , 6 2 
 
6 , 4 4 % 
 Equipamentos  e  software  
     
3 1 . 3 0 0 , 0 0 
 
2 , 0 8 % 
 Material  de  consumo         Livros/periódicos  técnicos         Outros  correlatos         Custos  incorridos  pela  instituição  
2 3 . 9 6 0 , 2 3 
 
2 4 . 1 0 8 , 6 6 
 
2 3 . 9 6 0 , 2 3 
 
2 3 . 9 6 0 , 2 3 
 
2 3 . 9 6 0 , 2 3 
 
2 9 6 . 8 5 7 , 7 0 
 
1 9 , 7 0 % 
 Total  de  recursos  financeiros  (R$)  
1 2 1 . 6 2 5 , 5 5 
 
1 2 2 . 3 7 8 , 9 8 
 
1 2 1 . 6 2 5 , 5 5 
 
1 2 1 . 6 2 5 , 5 5 
 
1 2 1 . 6 2 5 , 5 5 
 
1 . 5 0 6 . 8 9 1 , 9 0 
 
1 0 0 , 0 % 
    
4.  Das  Disposições  Gerais   O  presente  Plano  de  Trabalho  é  parte  integrante  do  36º  ACORDO  DE  COOPERAÇÃO  
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
    Fortaleza,  5  de  Janeiro  de  2026.  
  
______________________________________________________________
 UNIVERSIDADE  FEDERAL  DO  CEARÁ  CNPJ:  07.272.636/0001-31  PROF.  CUSTÓDIO  LUIS  SILVA  ALMEIDA  Reitor  CPF:  078.883.173-91  CONVENIADA        ______________________________________________________________  A  FUNDAÇÃO  ASTEF  –  FUNDAÇÃO  DE  APOIO  A  SERVIÇOS  TÉCNICOS,  ENSINO  E  
FOMENTO
 
A
 
PESQUISAS
 CNPJ:  08.918.421/0001-08  Joaquim  Perúcio  Pessoa  Filho  Diretor  Presidente  CPF:  404.268.903-53  INTERVENIENTE       ______________________________________________________________  DELL  COMPUTADORES  DO  BRASIL  LTDA

EMPRESA  Nome:  Mauricio  Helfer  CPF:  915.855.700-87
