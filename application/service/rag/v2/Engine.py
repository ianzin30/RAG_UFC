"""Composition root bridging the existing RAG facade to V2 components."""

from pathlib import Path
import hashlib
import time
from .Providers import ProviderRegistry
from .Cache import fingerprint, load_bundle, save_bundle
from .Documents import build_document_chunks
from .Retrieval import create_encoder, BGEReranker, HybridRetriever


class RAGEngine:
    def __init__(self, facade, llm_config, config):
        self.facade, self.config = facade, config
        self.providers = ProviderRegistry(llm_config)
        self.encoder = None
        self.retriever = None
        self.parents, self.catalog = {}, []
        self.last_trace = None

    def set_model(self, model):
        self.providers = ProviderRegistry(
            self.providers.config.model_copy(update={"model": model})
        )

    def load_collection(self, selection):
        from presentation.shared.CollectionSelection import (
            normalize_collection_selection,
            format_collection_selection_label,
        )

        facade = self.facade
        names = normalize_collection_selection(selection)
        if not names:
            raise ValueError("No collection selected")
        started = time.perf_counter()
        facade._emit_collection_progress(
            "collection_load_started", collection=str(selection)
        )
        files = facade._enumerate_collection_markdown_files(names)
        for record in list(files):
            sidecar = (facade.collections_root / record["relative_path"]).with_suffix(
                ".structure.json"
            )
            if sidecar.exists():
                files.append(
                    {
                        "relative_path": sidecar.relative_to(
                            facade.collections_root
                        ).as_posix(),
                        "sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
                    }
                )
        if self.encoder is None:
            self.encoder = create_encoder(self.config)
        chunk_settings = {
                "child_tokens": self.config.child_tokens,
                "parent_tokens": self.config.parent_tokens,
                "encoder": self.encoder.identity,
                "chunker": (
                    "structural_offsets_v3_heading_context"
                    if self.config.chunking_strategy == "legacy"
                    else self.config.chunking_strategy
                ),
                "tokenizer": self.encoder.tokenizer.name_or_path,
            }
        if self.config.chunking_strategy != "legacy":
            chunk_settings["chunker_sha256"] = hashlib.sha256(
                Path(__file__).with_name("Documents.py").read_bytes()
                + Path(__file__).with_name("MarkdownBlocks.py").read_bytes()
            ).hexdigest()
        facade._emit_collection_progress("collection_fingerprint_ready", file_count=len(files))
        key = fingerprint(files, chunk_settings)
        path = facade.project_root / "data/cache/rag_v2" / (key + ".npz")
        bundle = load_bundle(path)
        cache_hit = bundle is not None
        if bundle is None:
            facade._emit_collection_progress("collection_index_build_started", file_count=len(files))
            documents = facade._load_collection_documents(names)
            facade._emit_collection_progress("collection_documents_loaded", document_count=len(documents))
            chunks, parents, catalog = build_document_chunks(
                documents,
                facade.collections_root,
                self.encoder.tokenizer,
                self.config,
                facade._build_spreadsheet_chunks,
            )
            if not chunks:
                raise ValueError("No indexable text")
            facade._emit_collection_progress("index_embedding_started", total=len(chunks))
            vectors, sparse = self.encoder.encode([chunk.text for chunk in chunks])
            facade._emit_collection_progress("collection_cache_write_started")
            save_bundle(path, chunks, parents, catalog, vectors, sparse)
        else:
            chunks, parents, catalog, vectors, sparse = bundle
            for chunk in chunks:
                chunk.source = str(facade.collections_root / chunk.relative_path)
        self.parents, self.catalog = parents, catalog
        self.retriever = HybridRetriever(
            chunks,
            vectors,
            sparse,
            self.encoder,
            BGEReranker(self.config),
            self.config,
            key,
        )
        facade.collection_names, facade.collection_name = (
            names,
            format_collection_selection_label(names),
        )
        facade.document_registry = catalog
        facade.document_catalog = catalog
        facade.last_retrieval_focus = None
        self.load_diagnostics = {
            "cache_hit": cache_hit,
            "fingerprint": key,
            "latency_seconds": time.perf_counter() - started,
            "encoder": self.encoder.identity,
        }
        facade._emit_collection_progress(
            "collection_cache_restored" if cache_hit else "collection_cache_written",
            collection=facade.collection_name,
            completed=1,
            total=1,
        )

    def ask(self, question, history=None, diagnostics=False):
        from .Agents import AgentTeam
        from .Flow import RAGFlow

        if self.retriever is None:
            raise ValueError("No collection loaded")
        self.providers.calls.clear()
        self.providers.capture_payloads = diagnostics
        flow = RAGFlow(
            AgentTeam(self.providers),
            self.retriever,
            self.parents,
            self.catalog,
            self.config,
            self.encoder.tokenizer,
            lambda stage: self.facade._emit_response_status(stage, stage),
        )
        flow.state.original_question = question
        flow.state.history = list(history or [])
        started = time.perf_counter()
        try:
            state = flow.kickoff()
        except Exception as exc:
            # Keep the partially completed question inspectable even when an
            # agent or deterministic operation fails. Public response behavior
            # is unchanged; these fields belong to diagnostics.
            flow.diagnostics["query_plan"] = (
                flow.state.plan.model_dump() if flow.state.plan else None
            )
            flow.diagnostics["state"] = flow.state.model_dump()
            self.last_trace = {
                "trace_version": 2,
                "status": "error",
                "error": str(exc),
                "diagnostics": flow.diagnostics,
                "provider_calls": list(self.providers.calls),
                "evidence": [item.model_dump() for item in flow.state.evidence],
            }
            raise
        finally:
            flow.diagnostics["total_seconds"] = time.perf_counter() - started
        flow.diagnostics["query_plan"] = state.plan.model_dump()
        flow.diagnostics["state"] = state.model_dump()
        evidence_by_id = {item.evidence_id: item for item in state.evidence}
        ordered_ids = list(
            dict.fromkeys(eid for claim in state.claims for eid in claim.evidence_ids)
        )

        def source(item):
            occurrence = item.occurrences[-1] if item.occurrences else None
            return {
                "document_name": item.document_name,
                "chunk_kind": item.chunk_kind,
                "excerpt": item.excerpt,
                "source": item.source,
                "source_name": Path(item.source).name,
                "relative_path": item.relative_path,
                "evidence_id": item.evidence_id,
                "chunk_id": item.chunk_id,
                "parent_id": item.parent_id,
                "section_title": item.section_title,
                "provenance": item.provenance,
                "hop_id": occurrence.hop_id if occurrence else None,
                "reranker_score": occurrence.reranker_score if occurrence else None,
                "claim_ids": [
                    claim.claim_id
                    for claim in state.claims
                    if item.evidence_id in claim.evidence_ids
                ],
                "focus_spans": state.source_focus.get(item.evidence_id, []),
                "focus_status": state.source_focus_status.get(
                    item.evidence_id, "fallback"
                ),
            }

        plan = state.plan
        scope_ids = plan.scope.document_ids if plan else []
        matched = [
            entry["document_name"]
            for entry in self.catalog
            if entry["document_id"] in scope_ids
        ]
        legacy_fields = (
            "document_name",
            "chunk_kind",
            "excerpt",
            "source",
            "source_name",
            "relative_path",
        )
        trace = {
            "trace_version": 2,
            "route": plan.route,
            "answer_text": state.final_answer,
            "resolved_question": plan.resolved_question,
            "matched_documents": matched,
            "needs_document_refinement": state.status == "clarification_required",
            "resolver_status": state.status,
            "resolver_candidates": matched,
            "matched_aliases": [],
            "status": state.status,
            "abstained": state.status == "abstained",
            "document_scope": scope_ids,
            "target_document_name": matched[0] if len(matched) == 1 else None,
            "retrieval_intent": plan.intent,
            "sources": [
                {key: source(item)[key] for key in legacy_fields}
                for item in state.evidence[:6]
            ],
            "cited_sources": [source(evidence_by_id[eid]) for eid in ordered_ids],
            "evidence": [item.model_dump() for item in state.evidence],
            "claims": [claim.model_dump() for claim in state.claims],
            "stop_reason": state.stop_reason,
            "answer_repair_applied": state.repair_count > 0,
            "provider_calls": list(self.providers.calls),
        }
        if diagnostics:
            stages, catalog = {}, {}
            for hop_index, hop in enumerate(flow.diagnostics["hops"]):
                for stage, entries in hop["stages"].items():
                    stages[f"hop{hop['hop_id']}.query{hop_index}.{stage}"] = {
                        "candidate_ids": [entry["chunk_id"] for entry in entries]
                    }
            for chunk in self.retriever.chunks:
                catalog[chunk.chunk_id] = {
                    **chunk.model_dump(),
                    "candidate_id": chunk.chunk_id,
                }
            stages["candidate_pool"] = {
                "candidate_ids": list(
                    dict.fromkeys(
                        item["chunk_id"]
                        for hop in flow.diagnostics["hops"]
                        for item in hop.get("stages", {}).get("rrf", [])
                    )
                )
            }
            stages["selected_context"] = {
                "candidate_ids": [
                    chunk_id
                    for item in state.evidence
                    for chunk_id in (item.retrieved_chunk_ids or [item.chunk_id])
                ]
            }
            trace.update(
                diagnostics=flow.diagnostics,
                index_diagnostics=self.load_diagnostics,
                retrieved_candidates=flow.diagnostics["hops"],
                retrieval_stages=stages,
                retrieval_stage_order=list(stages),
                candidate_catalog=catalog,
                answer_context="\n\n".join(item.text for item in state.evidence),
            )
        self.last_trace = trace
        return trace
