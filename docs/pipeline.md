# Pipeline RAG V2

`RAGService` preserva os contratos públicos de coleção, modelo, respostas, diagnostics e callbacks. Sua implementação delega exclusivamente ao `RAGEngine`.

## Ingestão e índice

Uploads, Google Drive e scraping produzem Markdown. Docling pode produzir sidecars estruturais com proveniência real. Planilhas mantêm row records, people/entity chunks, perfis e metadados especializados.

`CollectionStore` enumera e lê Markdown UTF-8. `Documents` cria parents/children com IDs estáveis. O índice versionado combina dense, sparse, catálogo e parents em `data/cache/rag_v2/`. Fingerprints incluem conteúdo, sidecars e configuração documental; geração não invalida o índice.

## Retrieval

BGE-M3 produz vetores normalizados e pesos lexicais. Dense usa FAISS IndexFlatIP; escopo restrito cria um subconjunto exato somente com vetores permitidos, reutilizável em cache limitado.

Sparse acumula `sum(w_query(token) * w_document(token))` nos chunks permitidos. RRF soma `1 / (k + rank)` dos canais independentes. O cross-encoder BGE-reranker-v2-m3 reranqueia candidatos. Parents são recuperados por IDs.

## Agentes e resposta

CrewAI Flow compartilha estado tipado entre planejamento, pesquisa, raciocínio, síntese e verificação. Perguntas simples podem parar no primeiro round; buscas adaptativas respeitam o limite de hops, repetição e ausência de novidade.

Claims apontam para Evidence IDs. Verificação e um reparo limitado bloqueiam claims sem suporte; insuficiência central resulta em abstenção ou resposta parcial.

Depois da verificação, source_focus escolhe citações curtas literais, validadas com offsets. Falha de foco preserva a resposta verificada e usa a prévia de fallback.

## Contratos e observabilidade

Trace V2 contém plano/escopo, hops, rankings dense/sparse/RRF/reranker, evidências, claims, verificações, provider/modelo efetivo e latências.

`sources` permanece um campo legado de recuperação. `cited_sources` contém fontes citadas por claims aprovados; vazio não faz fallback para fontes recuperadas. UI e Telegram respeitam essa distinção. Históricos antigos continuam legíveis.

O Streamlit mostra prévias compactas expansíveis. Abrir fontes ou históricos não dispara agentes. Não existe pipeline V1 ativo.
