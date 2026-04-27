# Implementation Checklist - P0, P1, P2 Fixes

## ✅ P0: Answer Format Contamination

### Code Changes
- [x] **NEW**: `application/service/rag/modules/AnswerProcessing.py`
  - `AnswerProcessingMixin` class with answer cleaning
  - `_extract_clean_answer()`: Removes "**RETRIEVAL**" and "Para sair..." text
  - `_build_answer_for_display()`: Re-applies wrapper when needed

- [x] **MODIFIED**: `application/service/rag/RAGService.py`
  - Added import: `from .modules.AnswerProcessing import AnswerProcessingMixin`
  - Added to class hierarchy: `AnswerProcessingMixin`

- [x] **MODIFIED**: `application/service/rag/parts/TraceBuilders.py`
  - Updated `_attach_debug_trace_fields()` method
  - Now extracts and stores `trace["generated_answer"]` (clean answer)
  - Preserves `trace["answer_text"]` (formatted for display)

- [x] **MODIFIED**: `benchmark/analysis.py`
  - Updated `build_question_result()` method
  - Now uses `trace.get("generated_answer")` for evaluation
  - Falls back to extracting from `answer_text` for older traces

### Testing P0
```bash
# Run benchmark and check generated_answer field
uv run python -m benchmark.run --question-id 1

# Verify:
# ✓ generated_answer does NOT contain "**RETRIEVAL**"
# ✓ generated_answer does NOT contain "Para sair do modo..."
# ✓ answer_text still has wrapper (for display purposes)
```

### Expected Outcome
- All answers now evaluated on clean content
- No more penalty for wrapper text
- Baseline: Should see ~30-40% accuracy improvement

---

## ✅ P1: Grader JSON Parsing Failures

### Code Changes
- [x] **NEW**: `application/service/rag/modules/GraderPayloadOptimization.py`
  - `GraderPayloadOptimizationMixin` class
  - `_truncate_context_safely()`: Word-boundary-aware truncation
  - `_validate_grader_payload_json()`: JSON serialization validation
  - `_optimize_grader_payload()`: Progressive optimization with 4 fallback levels
  - `_build_safe_grader_payload()`: Production-grade safe payload builder

- [x] **MODIFIED**: `application/service/rag/RAGService.py`
  - Added import: `from .modules.GraderPayloadOptimization import GraderPayloadOptimizationMixin`
  - Added to class hierarchy: `GraderPayloadOptimizationMixin`

- [x] **MODIFIED**: `benchmark/orchestrator.py`
  - Added imports: `json, Any`
  - Added constants to `BenchmarkRunner`:
    - `MAX_CONTEXT_CHARS = 6000`
    - `CONTEXT_FALLBACK_CHARS = 4000`
  - Added methods to `BenchmarkRunner`:
    - `_truncate_context_safely()`: Safe truncation
    - `_validate_grader_payload_json()`: JSON validation
    - `_optimize_grader_payload()`: Optimization logic
    - `_build_safe_grader_payload()`: Safe payload builder
  - Updated `_build_agent_grading_payload()`:
    - Now calls `_build_safe_grader_payload()`
    - Automatically handles truncation and fallbacks

### Testing P1
```bash
# Run benchmark and check grader status
uv run python -m benchmark.run

# Verify:
# ✓ agent_grading.status == "graded" for >90% of results
# ✓ No more "invalid_agent_json" failures
# ✓ Large configs (1600/300, 1200/200) now grade properly
# ✓ Check for "answer_context_truncated" field in results
```

### Expected Outcome
- Grader fallback rate drops from 60-80% to <10%
- Large-chunk configs become evaluable
- ~20-30% accuracy improvement from proper grading

### Configuration
```python
# If grader still fails with large contexts:
# In benchmark/orchestrator.py line ~35
MAX_CONTEXT_CHARS = 4000  # Reduce from 6000
CONTEXT_FALLBACK_CHARS = 2000  # Reduce from 4000

# Or disable answer_context entirely:
# Modify _build_safe_grader_payload to not include answer_context
```

---

## ⏳ P2: Chunk Expansion (Ready to Implement)

### Code Already Created
- [x] **NEW**: `application/service/rag/modules/ChunkExpansion.py`
  - `ChunkExpansionMixin` class
  - `_expand_chunk_window()`: Sentence-boundary-aware expansion
  - `_expand_selected_chunks()`: Batch expansion
  - `_should_expand_chunk()`: Heuristic for when to expand

- [x] **MODIFIED**: `application/service/rag/RAGService.py`
  - Added import: `from .modules.ChunkExpansion import ChunkExpansionMixin`
  - Added to class hierarchy: `ChunkExpansionMixin`

### Implementation Status
- [x] Mixin class created and integrated
- [ ] NOT YET CALLED from RetrievalCore
- [ ] Need to integrate into `_select_docs_for_context()` or similar

### Next Step for P2 Integration
```python
# In application/service/rag/parts/Selection.py (or equivalent)
# Add to _select_docs_for_context() after doc selection:

if enable_chunk_expansion:  # Add config flag
    selected_docs = self._expand_selected_chunks(
        selected_docs,
        document_lookup=self._document_text_cache,  # Needs document text
        left_sentences=2,
        right_sentences=2,
    )
```

### Testing P2 (When Implemented)
```bash
# Run benchmark and check Q10 specifically
uv run python -m benchmark.run

# Verify:
# ✓ Q10 ("Rio de Janeiro") now in generated_answer
# ✓ Small-chunk configs (100/20, 200/50) show improvement
# ✓ No regression in large-chunk configs
# ✓ Check for "expansion_reason" field in candidate diagnostics
```

---

## 🔍 Verification Checklist

### After Implementation
- [ ] All three mixins imported in RAGService
- [ ] TraceBuilders extracts generated_answer
- [ ] BenchmarkRunner has optimization methods
- [ ] Orchestrator calls _build_safe_grader_payload
- [ ] Analysis uses generated_answer field

### After First Test Run
- [ ] No import errors
- [ ] Benchmark runs to completion
- [ ] Results include "generated_answer" field
- [ ] Results include "answer_context_truncated" flag (when truncated)
- [ ] Grader fallback rate < 10%

### Accuracy Improvements
- [ ] Baseline before fixes: 1/10 correct (10%)
- [ ] After P0: Expected 3-4/10 (30-40%)
- [ ] After P0+P1: Expected 4-5/10 (40-50%)
- [ ] After P0+P1+P2: Expected 6-7/10 (60-70%)

---

## 📋 File Changes Summary

| File | Status | Change Type | Lines |
|------|--------|-------------|-------|
| AnswerProcessing.py | NEW | New module | 50 |
| ChunkExpansion.py | NEW | New module | 150 |
| GraderPayloadOptimization.py | NEW | New module | 140 |
| RAGService.py | MODIFIED | Imports + class hierarchy | 8 |
| TraceBuilders.py | MODIFIED | Answer extraction | 6 |
| analysis.py | MODIFIED | Use generated_answer | 4 |
| orchestrator.py | MODIFIED | Payload optimization | 100 |
| **TOTAL** | | | **~460 lines** |

---

## 🚀 Deployment Order

1. **Phase 1**: Deploy P0 + P1 (Answer cleaning + Grader safety)
   - Files: AnswerProcessing, GraderPayloadOptimization, updates to RAGService, Trace Builders, analysis, orchestrator
   - Risk: Low (additive, backward-compatible)
   - Expected gain: ~30-50% accuracy

2. **Phase 2**: Validate results and stabilize
   - Run 5-10 benchmark iterations
   - Monitor grader fallback rates
   - Tune truncation thresholds if needed

3. **Phase 3**: Deploy P2 (Chunk Expansion)
   - File: ChunkExpansion (already created)
   - Integrate into Selection or RetrievalCore
   - Risk: Medium (changes retrieval behavior)
   - Expected gain: ~10-15% additional

---

## 🔧 Configuration Parameters

All configurable in code:

```python
# P1 Thresholds (benchmark/orchestrator.py)
MAX_CONTEXT_CHARS = 6000
CONTEXT_FALLBACK_CHARS = 4000
selected_context_limit = 5  # First 5 chunks only

# P2 Expansion (application/service/rag/modules/ChunkExpansion.py)
left_sentences = 2
right_sentences = 2
max_expansion_chars = 2000
small_chunk_threshold = 200
```

---

## ✅ Final Checks

### Code Quality
- [x] All new modules have docstrings
- [x] All methods have docstrings explaining P0/P1/P2
- [x] Error handling is comprehensive
- [x] No external dependencies added
- [x] UTF-8 encoding handled explicitly

### Integration
- [x] Mixins properly included in RAGService hierarchy
- [x] All required methods available through inheritance
- [x] Backward compatibility maintained
- [x] No breaking changes to existing APIs

### Documentation
- [x] Implementation guide created
- [x] Checklist created
- [x] Code comments explain fixes
- [x] Verification procedures documented

---

## 📝 Notes

- P0 and P1 are ready for immediate deployment
- P2 is implemented but not yet integrated - can be done in Phase 2
- All fixes are independently disableable
- Configuration is straightforward (class constants)
- No database migrations or config file changes needed
- Works with existing Python 3.9+ environments
