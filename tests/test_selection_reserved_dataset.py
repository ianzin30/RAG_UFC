import ast
import hashlib
import json
from collections import Counter
from pathlib import Path
from benchmark.evaluation.evidence import normalized


def test_reserved_source_positions_quotas_and_fact_separation():
    root = Path('benchmark/datasets/selection_generalization_v1')
    cases = json.loads((root / 'test/questions.json').read_text())
    rules = json.loads((root / 'test/evidence_v2_rules.json').read_text())
    audit = json.loads((root / 'test/source_audit.json').read_text())
    assert Counter(c['category'] for c in cases) == {
        'multi-hop': 10, 'cross-document': 10, 'single-document factual': 10}
    assert all(c['metadata']['outside_old_fields'] for c in cases)
    assert max(Counter(a for c in cases for a in c['metadata']['evidence_ids']).values()) <= 2
    assert len(audit['families_used']) == 13 and not audit['exact_old_quote_collisions']
    for rule in rules['anchors'].values():
        source = Path('data/collections/uploaded_files') / rule['document']
        raw = source.read_text()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == rule['source_sha256']
        for req in rule['requirements']:
            assert normalized(raw[req['source_start']:req['source_end']])[0] == req['text']
    assert audit['no_retrieval_results_used'] and not audit['independent_human_review']


def test_selector_boundary_excludes_gold_and_specific_resolver():
    text = Path('application/service/rag/v2/EvidenceSelection.py').read_text()
    modules = [node.module or '' for node in ast.walk(ast.parse(text)) if isinstance(node, ast.ImportFrom)]
    assert not any('benchmark' in m or 'Planning' in m or 'Directed' in m for m in modules)
    assert not any(value in text for value in ('expected_answer', 'FIELD_PATTERNS', 'TEMPLATES', 'meeting_dates', 'project_aliases', 'category'))
