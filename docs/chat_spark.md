# Testar o chat com a Spark

A aplicação mantém o RAG V2: planejamento, recuperação híbrida, resposta, verificação e fontes. O controlador experimental não foi integrado. Por decisão do usuário nesta etapa, a janela local é **16.384 tokens** e o contexto documental é **6.000 tokens BGE**. Esses números usam tokenizadores diferentes e não são intercambiáveis.

## Iniciar

Na raiz do projeto:

```sh
.venv/bin/python run_streamlit.py
```

Abra `http://127.0.0.1:8501`. O launcher traduz as seções nativas do TOML para flags do Streamlit. Para outra porta, acrescente `--server.port=8502`. Reinicie o processo depois de mudar a configuração ou o código; um serviço já preparado não recebe mudanças silenciosas durante uma pergunta.

A Spark requer a VPN do laboratório e `LLM_API_KEY` no ambiente ou `.env`. Nunca coloque a chave no TOML. Uma chave vazia bloqueia o envio com a mensagem `Preencha LLM_API_KEY no .env`.

O serviço local Ollama precisa servir `embeddinggemma:latest`. Os modelos BGE e os tokenizadores precisam estar previamente no cache local. O launcher usa esse cache (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` por padrão), sem baixar pesos durante o atendimento. A preparação pode construir um novo índice se a identidade do encoder ou os documentos mudarem. Isso não altera o corpus.

## Configuração efetiva

`config/config.toml` separa `[llm]`, `[rag_v2]`, `[benchmark.*]` e `[streamlit.*]`. O frontend não importa parâmetros do benchmark. Foram copiados explicitamente apenas os dois limites solicitados pelo usuário.

Overrides explícitos `LLM_BASE_URL` e `LLM_MODEL` no processo vencem o TOML. Valores legados dessas variáveis no `.env` só são aceitos quando concordam com o TOML; divergências bloqueiam a preparação com orientação de migração. A leitura não sobrescreve essas variáveis no processo. A credencial do processo vence a credencial do `.env`.

A janela é uma proteção local, não uma alteração de configuração da Spark. Toda requisição, inclusive reparo de JSON, confere entrada, reserva de saída do papel e margem de 512 tokens. Conteúdo vazio ou truncado é recusado. Thinking fica desligado, temperatura zero e seed 42. O esquema JSON segue no prompt; formato e referências são validados localmente, com até um reparo explícito. O provider Spark não envia `response_format` nem tenta outro modo após uma falha. Não há troca automática de modelo ou endpoint.

## Conversas e recuperação

O JSON continua compartilhado entre abas e sessões desta instalação. Não é um serviço com contas e histórico privado. Cada operação lê a versão atual, sob lock entre processos. Renderizar a tela não salva um snapshot antigo.

A primeira alteração de um histórico antigo cria `<arquivo>.v1.bak` antes da migração para o formato 2. Mensagens e fontes antigas são preservadas; identificadores e perfis ausentes não são inventados retroativamente. Nunca apague o backup para resolver um erro de leitura. Um arquivo corrompido bloqueia gravações e exige recuperação a partir de uma cópia íntegra.

Cada envio aceito registra seu turno antes de executar o RAG. Uma conversa aceita apenas um turno em andamento. Recarregar não repete chamadas; reenviar explicitamente é uma nova submissão. Erros e perguntas sem resposta concluída ficam fora do próximo histórico semântico. Abstenções, esclarecimentos e respostas parciais concluídas são preservados com seus estados.

Timeout ou interrupção deixam resultado desconhecido, sem repetição automática. Após falha de disco, mantenha a aba aberta e use **Tentar salvar novamente**: somente a gravação será repetida. Fechar a aba pode perder uma resposta que ainda estava somente na memória.

Para testes com histórico separado:

```sh
RAG_CHAT_HISTORY_PATH=/tmp/rag-chat-teste.json .venv/bin/python run_streamlit.py
```

## Fontes e diagnóstico

Fontes são vinculadas ao turno, deduplicadas e verificadas estruturalmente. Destaques precisam corresponder literalmente ao excerto. Fonte inválida gera aviso localizado e não destrói a resposta. A ausência explícita de citações não é substituída por candidatos recuperados.

**Detalhes da execução** mostra modelo, coleção, parâmetros, consumo e contagens. Uma execução do RAG pode fazer várias chamadas internas. Retries HTTP 429/5xx são limitados pelo cliente; reparos de JSON têm outro limite. Não há retry automático de timeout ou conexão com resultado desconhecido. Os logs operacionais não devem conter perguntas, documentos, respostas brutas ou credenciais.

## Verificar sem serviços reais

```sh
.venv/bin/python -m pytest tests/test_spark_chat_runtime.py tests/test_streamlit_chat_audit.py -q
.venv/bin/python -m streamlit run docs/analises/chat_spark_fixture.py --server.address=127.0.0.1 --server.port=8519 --browser.gatherUsageStats=false
```

A fixture usa a página da aplicação com RAG simulado, documentos sintéticos e armazenamento temporário. Ela não valida a Spark nem a qualidade documental.

Os replays históricos exigem o TOML e o código de suas assinaturas originais. A configuração antiga está preservada no `code.zip` da rodada. Não substitua hashes nem flexibilize verificações para retomar um experimento com esta aplicação modificada.
