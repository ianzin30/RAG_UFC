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
