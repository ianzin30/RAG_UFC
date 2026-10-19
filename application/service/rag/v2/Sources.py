"""Version-aware presentation: an empty cited_sources must stay empty."""

from copy import deepcopy


def displayed_sources(payload):
    if "cited_sources" in payload:
        return list(payload.get("cited_sources") or [])
    return list(payload.get("sources") or [])


def preserve_v2_fields(source, target):
    for key in (
        "trace_version",
        "cited_sources",
        "evidence",
        "claims",
        "source_focus",
        "source_focus_status",
        "document_scope",
        "status",
    ):
        if key in source:
            target[key] = deepcopy(source[key])
    return target


def normalize_presentation(payload):
    """Structural validation only, shared by new results and persisted messages."""
    from hashlib import sha256
    import json
    result = deepcopy(payload)
    warnings = list(result.get('source_warnings') or []) if isinstance(result.get('source_warnings', []), list) else []
    evidence = result.get('evidence')
    evidence_by_id = {str(e['evidence_id']): e for e in evidence if isinstance(e, dict) and e.get('evidence_id')} if isinstance(evidence, list) else None
    key = 'cited_sources' if 'cited_sources' in result else 'sources'
    entries = result.get(key, [])
    if not isinstance(entries, list):
        entries = []
        warnings.append('Lista de fontes inválida; a resposta foi preservada.')
    normalized, by_key = [], {}
    for source in entries:
        if not isinstance(source, dict):
            warnings.append('Uma fonte inválida foi omitida.')
            continue
        item = deepcopy(source)
        eid = str(item.get('evidence_id') or '')
        if key == 'cited_sources' and evidence_by_id is not None:
            origin = evidence_by_id.get(eid)
            if origin is None or any(item.get(f) and origin.get(f) and item[f] != origin[f] for f in ('chunk_id', 'parent_id', 'relative_path', 'source', 'excerpt')):
                warnings.append('Uma fonte sem vínculo com a evidência desta resposta foi omitida.')
                continue
        for field in ('document_name', 'chunk_kind', 'excerpt', 'relative_path', 'source', 'source_name', 'section_title'):
            item[field] = str(item.get(field) or '')
        item['document_name'] = item['document_name'] or 'documento'
        provenance = item.get('provenance') or []
        if not isinstance(provenance, list) or any(not isinstance(p, dict) for p in provenance):
            warnings.append('Metadados inválidos de uma fonte foram omitidos.')
        item['provenance'] = [p for p in provenance if isinstance(p, dict)] if isinstance(provenance, list) else []
        claims = item.get('claim_ids')
        item['claim_ids'] = list(dict.fromkeys(str(c) for c in claims)) if isinstance(claims, list) else []
        spans, text = [], item['excerpt']
        raw_spans = item.get('focus_spans') or []
        for span in raw_spans if isinstance(raw_spans, list) else []:
            if isinstance(span, dict):
                start, end, quote = span.get('start'), span.get('end'), span.get('quote')
                if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text) and quote == text[start:end]:
                    spans.append({**span, 'claim_ids': [str(c) for c in span.get('claim_ids', [])] if isinstance(span.get('claim_ids', []), list) else []})
                    continue
            warnings.append('Um destaque inconsistente foi omitido; confira o excerto da fonte.')
        item['focus_spans'] = spans
        identity = [eid, item.get('chunk_id'), item.get('parent_id'), item['relative_path'], item['source'], item['excerpt']]
        stable = sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:20]
        item['source_id'] = stable
        if stable in by_key:
            old = by_key[stable]
            old['claim_ids'] = list(dict.fromkeys(old['claim_ids'] + item['claim_ids']))
            for span in item['focus_spans']:
                if span not in old['focus_spans']: old['focus_spans'].append(span)
        else:
            by_key[stable] = item
            normalized.append(item)
    result[key] = normalized
    result['source_warnings'] = list(dict.fromkeys(str(w) for w in warnings))
    return result
