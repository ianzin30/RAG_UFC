"""Human-readable report rendering for benchmark results."""

from __future__ import annotations

import re
from collections import Counter


def _clean_generated_answer(raw: str) -> str:
    """Strip UI-mode headers and navigation hints from the answer text."""
    text = raw.strip()
    text = re.sub(r"^\*\*[A-ZÁÉÍÓÚÀÃÕÂÊÔ ]+\*\*\s*\n+", "", text)
    text = re.sub(r"\n+Para sair do modo.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()


def _safe_cell(text: str) -> str:
    """Sanitise text for use inside a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _verdict_icon(failure_class: str, grounding_status: str) -> str:
    if failure_class and failure_class not in ("no_failure", "none", "unknown", ""):
        return "❌"
    if grounding_status == "weakly_grounded":
        return "⚠️"
    return "✅"


def _failure_label(classification: str) -> str:
    labels = {
        "no_failure": "Sem falha",
        "generation_failure": "Falha na geração",
        "retrieval_failure": "Falha na recuperacao",
        "selection_failure": "Falha na selecao",
        "document_resolution_failure": "Falha de documento explicito",
        "benchmark_data_mismatch": "Dado esperado ausente",
    }
    return labels.get(classification, classification or "desconhecida")


def _grounding_label(status: str) -> str:
    labels = {
        "grounded": "✅ Bem fundamentada",
        "weakly_grounded": "⚠️ Fracamente fundamentada",
        "ungrounded": "❌ Sem fundamentação",
        "unsupported": "❌ Sem fundamentação",
        "unknown": "Desconhecida",
    }
    return labels.get(status, status or "desconhecida")


def _chunk_kind_label(kind: str) -> str:
    labels = {
        "document_profile": "perfil",
        "section_overview": "resumo",
        "section_detail": "trecho",
        "entity_index": "entidades",
        "list_block": "lista",
    }
    return labels.get(kind, kind)


def _format_chunk_simple(candidate: dict, index: int) -> str:
    doc = str(candidate.get("document_name") or "doc").strip()
    kind = str(candidate.get("chunk_kind") or "text").strip()
    section = str(candidate.get("section_title") or "").strip()
    excerpt = str(candidate.get("excerpt") or "").strip()[:100]
    priority_components = {
        str(key): int(value)
        for key, value in dict(candidate.get("priority_score_components") or {}).items()
        if int(value) != 0
    }

    loc = f"**{doc}**"
    if section:
        loc += f" › {section}"
    loc += f" ({_chunk_kind_label(kind)})"

    line = f"{index}. {loc}"
    if excerpt:
        line += f"\n   > {excerpt}…"
    if priority_components:
        component_text = ", ".join(
            f"{name}={value}" for name, value in priority_components.items()
        )
        line += f"\n   - prioridade: {component_text}"
    return line


def _format_rank_movement_simple(entries: list) -> list[str]:
    stage_short = {
        "dense_mmr": "mmr",
        "lexical": "lex",
        "candidate_pool": "pool",
        "llm_selected": "sel-llm",
        "selected_context": "sel",
    }

    lines = []
    for entry in entries:
        doc = str(entry.get("document_name") or "doc").strip()
        positions = entry.get("stage_positions") or {}

        pos_str = " → ".join(
            f"{stage_short.get(stage, stage)}={positions[stage]}"
            for stage in ["dense_mmr", "lexical", "candidate_pool", "llm_selected", "selected_context"]
            if positions.get(stage) is not None
        )

        if pos_str:
            lines.append(f"- {doc}: {pos_str}")
        else:
            lines.append(f"- {doc}: não recuperado")

    return lines


def _format_evidence_span(span: dict, index: int) -> str:
    doc = str(span.get("document_name") or "doc").strip()
    kind = str(span.get("chunk_kind") or "text").strip()
    section = str(span.get("section_title") or "").strip()
    excerpt = str(span.get("text") or "").strip()[:140]
    components = {
        str(key): int(value)
        for key, value in dict(span.get("score_components") or {}).items()
        if int(value) != 0
    }

    line = f"{index}. **{doc}**"
    if section:
        line += f" › {section}"
    line += f" ({_chunk_kind_label(kind)})"
    if excerpt:
        line += f"\n   > {excerpt}…"
    if components:
        component_text = ", ".join(f"{name}={value}" for name, value in components.items())
        line += f"\n   - span: {component_text}"
    return line


def render_markdown_report(run_payload: dict[str, object]) -> str:
    results = list(run_payload.get("results") or [])
    failure_counts = Counter(
        str((r.get("failure") or {}).get("classification") or "unknown")
        for r in results
    )
    grounding_counts = Counter(
        str((r.get("grounding") or {}).get("grounding_status") or "unknown")
        for r in results
    )

    total = len(results)
    ok_count = failure_counts.get("no_failure", 0)
    grounded_count = grounding_counts.get("grounded", 0)
    agent_graded_count = sum(
        1 for result in results if str((result.get("agent_grading") or {}).get("status") or "") == "graded"
    )
    agent_fallback_count = sum(
        1 for result in results if str((result.get("agent_grading") or {}).get("status") or "") == "fallback"
    )
    retrieval_metrics = [dict((result.get("retrieval") or {}).get("metrics") or {}) for result in results]
    source_in_pool_count = sum(1 for metrics in retrieval_metrics if metrics.get("source_document_in_pool"))
    expected_in_pool_count = sum(1 for metrics in retrieval_metrics if metrics.get("expected_answer_in_pool"))
    expected_in_context_count = sum(1 for metrics in retrieval_metrics if metrics.get("expected_answer_in_context"))
    avg_context_hit_rate = (
        sum(float(metrics.get("context_hit_rate") or 0.0) for metrics in retrieval_metrics) / total
        if total
        else 0.0
    )
    pct_ok = f"{ok_count / total * 100:.0f}%" if total else "—"
    pct_grounded = f"{grounded_count / total * 100:.0f}%" if total else "—"

    run_id = str(run_payload.get("run_id") or "")
    generated_at = str(run_payload.get("generated_at") or "")
    collections = ", ".join(list(run_payload.get("collections") or [])) or "—"

    lines: list[str] = [
        "# Relatório RAG",
        "",
        f"**Execução:** {run_id}  ",
        f"**Data:** {generated_at}  ",
        f"**Coleção:** {collections}  ",
        "",
    ]

    # Config
    config_snapshot = dict(run_payload.get("config_snapshot") or {})
    if config_snapshot:
        rag_config = dict(config_snapshot.get("rag") or {})
        model = config_snapshot.get("ufc_model_name", "—")
        strict = rag_config.get("strict_grounding")
        min_score = rag_config.get("min_evidence_score")
        lines.extend([
            f"**Modelo:** `{model}` | **Modo estrito:** {'Sim' if strict else 'Não'} | **Min score:** `{min_score}`",
            "",
        ])

    # Summary
    lines.extend([
        "## Resumo",
        "",
        f"- Perguntas: {total}",
        f"- Sem falha: {ok_count}/{total} ({pct_ok})",
        f"- Bem fundamentada: {grounded_count}/{total} ({pct_grounded})",
        f"- Documento-fonte no pool: {source_in_pool_count}/{total}",
        f"- Resposta esperada no pool: {expected_in_pool_count}/{total}",
        f"- Resposta esperada no contexto: {expected_in_context_count}/{total}",
        f"- Hit rate medio do contexto: {avg_context_hit_rate:.2f}",
        f"- Avaliacao por agente: {agent_graded_count}/{total}",
        f"- Fallback deterministico: {agent_fallback_count}/{total}",
    ])

    non_ok = {cls: cnt for cls, cnt in failure_counts.items() if cls != "no_failure"}
    if non_ok:
        lines.append("")
        for cls, cnt in non_ok.items():
            lines.append(f"- {_failure_label(cls)}: {cnt}×")

    lines.extend(["", "---", ""])

    # Per-question
    for result in results:
        q_data = dict(result.get("question_data") or {})
        retrieval = dict(result.get("retrieval") or {})
        grounding = dict(result.get("grounding") or {})
        failure = dict(result.get("failure") or {})
        generation = dict(result.get("generation") or {})
        agent_grading = dict(result.get("agent_grading") or {})
        metrics = dict(retrieval.get("metrics") or {})

        failure_class = str(failure.get("classification") or "")
        grounding_status = str(grounding.get("grounding_status") or "")
        icon = _verdict_icon(failure_class, grounding_status)
        q_id = q_data.get("id", "?")

        clean_ans = _clean_generated_answer(str(q_data.get("generated_answer") or ""))
        expected = str(q_data.get("expected_answer") or "—")
        question = str(q_data.get("question") or "")
        top_docs = ", ".join(list(retrieval.get("top_documents") or [])) or "—"

        selected_ids = list(((retrieval.get("stages") or {}).get("selected_context") or {}).get("candidate_ids") or [])
        candidate_catalog = dict(retrieval.get("candidate_catalog") or {})
        selected_chunks = [
            dict(candidate_catalog.get(cid) or {})
            for cid in selected_ids
            if dict(candidate_catalog.get(cid) or {})
        ]
        selected_evidence_spans = list(retrieval.get("selected_evidence_spans") or [])
        missed_hits = list(retrieval.get("missed_relevant_corpus_hits") or [])
        rank_movement = list(retrieval.get("rank_movement") or [])
        failure_notes = list(failure.get("notes") or [])
        dominant_candidate = dict(generation.get("consensus_dominant_candidate") or {})
        answer_candidates = list(
            generation.get("candidate_consensus_details")
            or generation.get("explicit_answer_candidates")
            or []
        )

        lines.extend([
            f"## {icon} Q{q_id}",
            "",
            f"**{question}**",
            "",
            f"| | |",
            f"|---|---|",
            f"| Gerado | {_safe_cell(clean_ans)} |",
            f"| Esperado | {_safe_cell(expected)} |",
            f"| Fundamentação | {_grounding_label(grounding_status)} |",
            f"| Falha | `{failure_class or 'no_failure'}` |",
            f"| Avaliador | `{agent_grading.get('status') or 'deterministic'}` |",
            f"| Documentos | {top_docs} |",
            f"| Fonte no pool | {'sim' if metrics.get('source_document_in_pool') else 'nao'}"
            f"{' (rank ' + str(metrics.get('source_document_rank')) + ')' if metrics.get('source_document_rank') else ''} |",
            f"| Esperado no contexto | {'sim' if metrics.get('expected_answer_in_context') else 'nao'} |",
        ])

        if failure_notes:
            lines.append(f"| Notas | {_safe_cell(failure_notes[0])} |")

        lines.append("")

        lines.extend([
            "<details>",
            "<summary>📋 Detalhes</summary>",
            "",
        ])

        if selected_evidence_spans:
            lines.append("**Evidencia focalizada:**")
            lines.append("")
            for i, span in enumerate(selected_evidence_spans[:3], 1):
                lines.append(_format_evidence_span(span, i))
            lines.append("")

        if selected_chunks:
            lines.append("**Trechos usados:**")
            lines.append("")
            for i, chunk in enumerate(selected_chunks[:4], 1):
                lines.append(_format_chunk_simple(chunk, i))
            lines.append("")

        if missed_hits:
            lines.append("**Evidências perdidas:**")
            lines.append("")
            for hit in missed_hits[:3]:
                doc = str(hit.get("document_name") or "—")
                exc = str(hit.get("excerpt") or "").strip()[:80]
                lines.append(f"- {doc}: {exc}…")
            lines.append("")

        if rank_movement:
            lines.append("**Ranking por etapa:**")
            lines.append("")
            lines.extend(_format_rank_movement_simple(rank_movement))
            lines.append("")

        if dominant_candidate or generation.get("answer_repair_applied") or generation.get("answer_shape"):
            lines.append("**Consenso da resposta:**")
            lines.append("")
            if generation.get("answer_shape"):
                lines.append(f"- Forma inferida: `{generation['answer_shape']}`")
            lines.append(f"- Origem final: `{generation.get('final_answer_origin') or 'llm'}`")
            if generation.get("answer_matches_top_evidence_span") is not None:
                lines.append(
                    f"- Seguiu evidencia focalizada: `{'sim' if generation.get('answer_matches_top_evidence_span') else 'nao'}`"
                )
            if generation.get("answer_ignored_top_evidence_span"):
                lines.append("- Divergiu do trecho focalizado principal.")
            if generation.get("answer_repair_applied"):
                lines.append(f"- Reparo aplicado: `{generation.get('answer_repair_reason') or 'sim'}`")
            if dominant_candidate:
                lines.append(
                    "- Candidato dominante: "
                    f"`{dominant_candidate.get('text') or '—'}` "
                    f"(consenso={dominant_candidate.get('consensus_score') or dominant_candidate.get('score') or 0}, "
                    f"mencoes={dominant_candidate.get('mention_count') or dominant_candidate.get('mentions') or 0})"
                )
            for candidate in answer_candidates[:3]:
                lines.append(
                    "- Evidencia candidata: "
                    f"`{candidate.get('text') or '—'}` "
                    f"(consenso={candidate.get('consensus_score') or candidate.get('score') or 0}, "
                    f"mencoes={candidate.get('mention_count') or candidate.get('mentions') or 0}, "
                    f"alinhamento={candidate.get('question_alignment_score') or 0})"
                )
            lines.append("")

        lines.extend(["</details>", "", ""])

    return "\n".join(lines).strip() + "\n"
