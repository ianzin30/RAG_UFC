"""Collection loading and cache restore helpers."""
# Simple: Load document collections and manage search cache

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS

from presentation.shared.CollectionSelection import (
    format_collection_selection_label,
    normalize_collection_selection,
)
from presentation.shared.Config import UPLOAD_COLLECTION_NAME
from ..Cache import (
    build_file_hash_record,
    build_rag_index_fingerprint,
    build_rag_index_fingerprint_inputs,
    get_rag_index_cache_dir,
    read_rag_index_manifest,
    write_rag_index_manifest,
)
from ..Constants import RAG_INDEX_CACHE_VERSION, ROOT_COLLECTION_KEY


# Este mixin cuida da carga da colecao e do cache persistente do indice vetorial.
class RAGServiceCollectionLoadingMixin:
    def set_collection_progress_callback(self, callback) -> None:
        self._collection_progress_callback = callback if callable(callback) else None

    def _emit_collection_progress(self, event: str, **payload) -> None:
        callback = getattr(self, "_collection_progress_callback", None) or getattr(
            self, "_benchmark_progress_callback", None
        )
        if not callable(callback):
            return
        try:
            callback({"event": event, **payload})
        except Exception:
            pass

    # Esta funcao traduz o nome selecionado para a pasta real da colecao.
    def _resolve_collection_path(self, selected_collection: str) -> Path:
        if selected_collection in {ROOT_COLLECTION_KEY, UPLOAD_COLLECTION_NAME}:
            return self.collections_root
        return self.collections_root / selected_collection

    # Este snapshot do splitter entra no fingerprint para invalidar caches antigos automaticamente.
    def _get_text_splitter_config(self) -> dict[str, int | list[str]]:
        return {
            "chunk_size": int(getattr(self.text_splitter, "_chunk_size", 0) or 0),
            "chunk_overlap": int(getattr(self.text_splitter, "_chunk_overlap", 0) or 0),
            "separators": list(getattr(self.text_splitter, "_separators", []) or []),
        }

    # Esta etapa enumera os .md e calcula os hashes que definem o fingerprint da colecao.
    def _enumerate_collection_markdown_files(self, collection_names: list[str]) -> list[dict[str, str]]:
        fingerprint_files: dict[str, dict[str, str]] = {}
        for selected_collection in collection_names:
            collection_path = self._resolve_collection_path(selected_collection)
            if not collection_path.exists():
                raise Exception(f"Collection '{selected_collection}' not found.")

            markdown_files = sorted(path for path in collection_path.rglob("*.md") if path.is_file())
            if not markdown_files:
                raise Exception(f"No documents found in collection '{selected_collection}'.")

            for file_path in markdown_files:
                record = build_file_hash_record(file_path, self.collections_root)
                fingerprint_files.setdefault(record["relative_path"], record)
        return [fingerprint_files[key] for key in sorted(fingerprint_files)]

    # Esta carga so acontece em cache miss ou quando o cache antigo ficou invalido.
    def _load_collection_documents(self, collection_names: list[str]) -> list:
        documents = []
        for selected_collection in collection_names:
            collection_path = self._resolve_collection_path(selected_collection)
            loader = DirectoryLoader(
                str(collection_path),
                glob="**/*.md",
                show_progress=True,
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"},
            )
            loaded_documents = loader.load()
            if not loaded_documents:
                raise Exception(f"No documents found in collection '{selected_collection}'.")

            for document in loaded_documents:
                document.metadata["collection_name"] = selected_collection
            documents.extend(loaded_documents)
        return documents

    # Esta etapa transforma documentos crus em chunks e em um catalogo consultavel.
    def _build_index_state(self, documents: list) -> tuple[list, list[dict], dict[str, list]]:
        chunks = []
        document_registry = {}
        document_seeds = {}
        document_chunk_buckets = {}
        spreadsheet_chunk_index = {}
        document_total = len(documents)
        self._emit_collection_progress(
            "index_chunking_started",
            completed=0,
            total=document_total,
            chunk_count=0,
        )

        for document_index, document in enumerate(documents, start=1):
            document.page_content = self._normalize_whitespace(document.page_content)
            source = document.metadata.get("source")
            document_name = self._extract_document_name(document.page_content, source)
            document_type = self._extract_document_type(document.page_content)
            document.metadata["document_name"] = document_name
            document.metadata["document_name_normalized"] = self._normalize_identifier(document_name)
            document.metadata["document_stem_normalized"] = self._normalize_identifier(Path(document_name).stem)
            document.metadata["document_type"] = document_type

            header = self._extract_document_header(document.page_content)
            if document_type == "spreadsheet":
                document_chunks = self._build_spreadsheet_chunks(document, header)
                spreadsheet_chunk_index.setdefault(document_name, []).extend(document_chunks)
            else:
                document_chunks = self._build_generic_chunks(document, header)
            chunks.extend(document_chunks)
            document_chunk_buckets.setdefault(document_name, []).extend(document_chunks)

            existing_seed = document_seeds.get(document_name)
            if existing_seed is None or len(document.page_content) >= len(str(existing_seed.get("text") or "")):
                document_seeds[document_name] = {
                    "document_name": document_name,
                    "document_type": document_type,
                    "text": document.page_content,
                    "source": source,
                }

            self._emit_collection_progress(
                "index_chunking_progress",
                completed=document_index,
                total=document_total,
                chunk_count=len(chunks),
                document_name=document_name,
            )

        for document_name, seed in document_seeds.items():
            document_registry[document_name] = self._build_document_registry_entry(
                document_name=document_name,
                document_type=str(seed.get("document_type") or "document"),
                text=str(seed.get("text") or ""),
                source=str(seed.get("source") or "") or None,
                chunks=document_chunk_buckets.get(document_name, []),
            )

        return chunks, list(document_registry.values()), spreadsheet_chunk_index

    def _build_vector_store_from_chunks(self, chunks: list):
        texts = [chunk.page_content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [getattr(chunk, "id", None) for chunk in chunks]
        kwargs = {"ids": ids} if any(ids) else {}
        chunk_total = len(texts)
        batch_size = max(1, int(getattr(self, "embedding_batch_size", 8) or 8))
        embeddings = []

        self._emit_collection_progress(
            "index_embedding_started",
            completed=0,
            total=chunk_total,
            batch_size=batch_size,
        )
        for start in range(0, chunk_total, batch_size):
            end = min(start + batch_size, chunk_total)
            embeddings.extend(self.embeddings.embed_documents(texts[start:end]))
            self._emit_collection_progress(
                "index_embedding_progress",
                completed=end,
                total=chunk_total,
                batch_size=batch_size,
            )

        self._emit_collection_progress(
            "index_faiss_build_started",
            completed=0,
            total=1,
            chunk_count=chunk_total,
        )
        vector_store = FAISS.from_embeddings(
            zip(texts, embeddings),
            self.embeddings,
            metadatas=metadatas,
            **kwargs,
        )
        self._emit_collection_progress(
            "index_faiss_build_completed",
            completed=1,
            total=1,
            chunk_count=chunk_total,
        )
        return vector_store

    # Este retriever aplica MMR para equilibrar relevancia e diversidade dos trechos.
    def _build_retriever(self):
        retrieval_config = getattr(self, "retrieval_config", None)
        return self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": int(getattr(retrieval_config, "base_search_k", 6)),
                "fetch_k": int(getattr(retrieval_config, "base_fetch_k", 30)),
                "lambda_mult": float(getattr(retrieval_config, "base_lambda_mult", 0.2)),
            },
        )

    # Esta leitura inspeciona os documentos guardados no docstore do FAISS.
    def _get_vector_store_documents(self) -> list:
        if self.vector_store is None:
            return []

        docstore = getattr(self.vector_store, "docstore", None)
        documents = getattr(docstore, "_dict", None)
        if not isinstance(documents, dict):
            return []
        return list(documents.values())

    # Esta reconstrucao reagrupa os chunks de planilha apos restaurar o indice salvo.
    def _rebuild_spreadsheet_chunk_index(self) -> dict[str, list]:
        spreadsheet_chunk_index: dict[str, list] = {}
        for chunk in self._get_vector_store_documents():
            metadata = getattr(chunk, "metadata", {}) or {}
            if metadata.get("document_type") != "spreadsheet":
                continue

            document_name = str(metadata.get("document_name") or "").strip()
            if not document_name:
                continue
            spreadsheet_chunk_index.setdefault(document_name, []).append(chunk)
        return spreadsheet_chunk_index

    # Esta etapa restaura o estado de runtime a partir do cache local persistido.
    def _restore_cached_collection(
        self,
        cache_dir: Path,
        manifest: dict,
        collection_names: list[str],
    ) -> None:
        document_registry = manifest.get("document_registry")
        if not isinstance(document_registry, list):
            raise ValueError("Invalid cached document registry.")

        self.vector_store = FAISS.load_local(
            str(cache_dir),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        self.collection_names = list(manifest.get("selected_collections") or collection_names)
        self.collection_name = str(
            manifest.get("collection_label") or format_collection_selection_label(collection_names)
        )
        self.document_registry = list(document_registry)
        self.document_catalog = self.document_registry
        self.spreadsheet_chunk_index = self._rebuild_spreadsheet_chunk_index()
        self.last_retrieval_focus = None
        self.retriever = self._build_retriever()

    # Esta e a porta principal de carga, com tentativa de cache antes do rebuild completo.
    def load_collection(self, collection_name):
        # Primeiro normalizamos a selecao e montamos o fingerprint da colecao.
        collection_names = normalize_collection_selection(collection_name)
        if not collection_names:
            raise Exception("No collection selected.")

        collection_label = format_collection_selection_label(collection_names)
        self._emit_collection_progress(
            "collection_load_started",
            collection=collection_label,
            completed=0,
            total=1,
        )
        file_hashes = self._enumerate_collection_markdown_files(collection_names)
        splitter_config = self._get_text_splitter_config()
        fingerprint_inputs = build_rag_index_fingerprint_inputs(
            selected_collections=collection_names,
            file_hashes=file_hashes,
            embedding_model_name=self.embedding_model_name,
            embedding_quantization=self.embedding_quantization,
            embedding_max_length=self.embedding_max_length,
            splitter_config=splitter_config,
            cache_version=RAG_INDEX_CACHE_VERSION,
        )
        fingerprint = build_rag_index_fingerprint(fingerprint_inputs)
        cache_dir = get_rag_index_cache_dir(self.rag_index_cache_root, fingerprint)
        manifest = read_rag_index_manifest(cache_dir)
        self._emit_collection_progress(
            "collection_fingerprint_ready",
            collection=collection_label,
            completed=1,
            total=1,
            file_count=len(file_hashes),
            cache_dir=str(cache_dir),
            splitter=splitter_config,
        )

        # Se o cache for valido, pulamos a etapa cara de leitura, chunking e indexacao.
        if manifest is not None:
            try:
                self._emit_collection_progress(
                    "collection_cache_restore_started",
                    collection=collection_label,
                    completed=0,
                    total=1,
                    cache_dir=str(cache_dir),
                )
                self._restore_cached_collection(cache_dir, manifest, collection_names)
                self._emit_collection_progress(
                    "collection_cache_restored",
                    collection=collection_label,
                    completed=1,
                    total=1,
                    cache_dir=str(cache_dir),
                )
                return
            except Exception:
                pass

        # Em cache miss, seguimos pelo pipeline completo e persistimos o resultado ao final.
        self._emit_collection_progress(
            "collection_index_build_started",
            collection=collection_label,
            completed=0,
            total=1,
            file_count=len(file_hashes),
            cache_dir=str(cache_dir),
        )
        documents = self._load_collection_documents(collection_names)
        self._emit_collection_progress(
            "collection_documents_loaded",
            collection=collection_label,
            completed=len(documents),
            total=len(file_hashes),
            document_count=len(documents),
        )
        chunks, document_registry, spreadsheet_chunk_index = self._build_index_state(documents)

        cache_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = self._build_vector_store_from_chunks(chunks)
        self._emit_collection_progress(
            "collection_cache_write_started",
            collection=collection_label,
            completed=0,
            total=1,
            cache_dir=str(cache_dir),
        )
        self.vector_store.save_local(str(cache_dir))
        self.collection_names = collection_names
        self.collection_name = collection_label
        self.document_registry = document_registry
        self.document_catalog = self.document_registry
        self.spreadsheet_chunk_index = spreadsheet_chunk_index
        self.last_retrieval_focus = None
        self.retriever = self._build_retriever()

        write_rag_index_manifest(
            cache_dir,
            {
                "fingerprint": fingerprint,
                "fingerprint_inputs": fingerprint_inputs,
                "document_registry": self.document_registry,
                "selected_collections": self.collection_names,
                "collection_label": self.collection_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self._emit_collection_progress(
            "collection_cache_written",
            collection=collection_label,
            completed=1,
            total=1,
            cache_dir=str(cache_dir),
        )
