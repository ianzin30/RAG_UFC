# Auditoria isolada do chat

O objetivo é reproduzir o comportamento atual, inclusive defeitos. Os testes verdes **não indicam correções**. Nenhum arquivo de produção é alterado por estes testes; serviços, documentos e armazenamento são substituídos por dados temporários.

Na raiz do repositório:

```sh
.venv/bin/python -m pytest tests/test_streamlit_chat_audit.py -q
```

Para inspecionar a interface com dados sintéticos, sem modelo ou retriever:

```sh
.venv/bin/python -m streamlit run docs/analises/streamlit_audit_app.py --server.address 127.0.0.1 --server.port 8519 --server.headless true --browser.gatherUsageStats false
```

Abra `http://127.0.0.1:8519`. Selecione um cenário na lateral e envie uma pergunta. A espera é simulada. Não use esta interface de teste para conversas institucionais. Encerre com Ctrl+C.

O relatório completo, comando dos 134 testes, achados, inventários, evidências e limitações estão em `run_01/relatorio.md`. O resultado visual está em `docs/resultado_auditoria_chat_streamlit_2026-10-19.html`.

Para reconstruir os relatórios a partir dos resultados já salvos:

```sh
.venv/bin/python docs/analises/build_streamlit_audit_report.py
```

O gerador também escreve uma cópia visual em `~/.agent/diagrams/`. A captura do navegador usa Chrome headless com perfil temporário: `run_01/browser_probe.py` registra o roteiro executado, mas seus caminhos e estado local precisam ser adaptados para outra máquina. As capturas não substituem os testes automatizados.

`protected_before.json` e `preservation.json` comprovam a preservação dos arquivos capturados. `manifest.json` registra hashes da implementação da auditoria e dos artefatos desta execução. Credenciais não fazem parte desses arquivos.
