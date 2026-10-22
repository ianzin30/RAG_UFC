# From research candidate to application release

A better metric does not make a strategy part of the application. A strategy reaches
QwenRAG only through a versioned core release whose evaluated pipeline matches what
the release ships, with an explicit maintainer decision.

## The pieces

| Piece | Where | Answers |
|---|---|---|
| Candidate registry | `benchmark/promotion/registry.json` | What is this strategy, where is it implemented, at which scope was it validated (component, pipeline, application), what would promotion require, what does the evidence say? |
| Strategy status in the core | `rag_ufc_core/strategies.py` | Which core modules are experimental; a test proves the application pipeline cannot import them |
| Pipeline identity | `rag_ufc_core.identity.pipeline_identity` | Which core source, configuration, models and index format ran |
| Release manifest | `rag_ufc_core/RELEASE.json` (inside the wheel) | Which pipeline this release is approved to run, its index format, approval decision and evidence (with hashes) |
| Release record | `releases/rag-ufc-core/<version>.json` | Commit, source fingerprint, wheel hash and install line of the published release; maintainer sign-off |
| Application pin | QwenRAG `core-release.lock.json` + dependency on the commit | Which release the application adopted; checked at startup |

Validation scopes are kept apart:

* **component** — a retrieval, selection or representation component improved under the
  tested conditions (Track B replays, E04's single-query completeness);
* **pipeline** — the full RAGFlow pipeline improved on a protocol;
* **application** — the application runs the intended pipeline and exposes its results
  (QwenRAG's adoption check and integration tests).

A component result never stands in for a pipeline result. `python -m benchmark.promotion
config-identity --llm-section benchmark.llm --compare-release` shows, for example, that the
frozen benchmark generation profile (vLLM, sampling options, answer budget 768) differs from
the released application pipeline (Spark, answer budget 2048) in five fields.

## Workflow

1. **Develop the candidate** against the current baseline: benchmark code, or core code behind
   a setting whose default keeps the baseline. Record it in the registry with status
   `experimental` and `validation_scope`.
2. **Identify what ran.** For each evaluation run, store
   `python -m benchmark.promotion identity --config <run config> --out <run>/pipeline_identity.json`
   (for historical runs: `config-identity --code-zip <run>/code.zip --llm-section …`).
3. **Evaluate** against the official baseline with the relevant frozen protocol (Track A/B).
   Review regressions, citation failures, wrong answers and missing evidence, not only aggregates.
4. **Approve or not.** A maintainer records the decision in the registry (`approved` +
   evidence), or keeps `experimental`/`rejected`.
5. **Integrate into the core** if needed: wire the strategy into `Flow`/`Engine` (making
   `strategies.py` say so), or change the default configuration. If the searchable text changes,
   define a new `REPRESENTATION_ID` in `identity.py` (old indexes become incompatible).
6. **Evaluate the release candidate itself**: the exact core commit and configuration that will
   ship, at pipeline scope. The registry's `released_in` names the version.
7. **Cut the release**: bump `__version__`, then

   ```bash
   uv run python -m benchmark.promotion manifest --version X.Y.Z --kind improvement \
     --status approved --approved-by "<maintainer>" --approved-at YYYY-MM-DD \
     --candidate <registry id> --evidence <docs and manifests> \
     --evaluation-scope pipeline --evaluation-statement "<what was shown and what was not>"
   git commit …                                   # package + RELEASE.json
   uv build packages/rag-ufc-core -o dist/
   uv run python -m benchmark.promotion record --wheel dist/rag_ufc_core-X.Y.Z-py3-none-any.whl \
     --tag rag-ufc-core-vX.Y.Z
   git tag rag-ufc-core-vX.Y.Z; git push origin <branch> rag-ufc-core-vX.Y.Z
   uv run python -m benchmark.promotion check
   ```

   `manifest` refuses `approved` without a maintainer and date, and refuses candidates the
   registry does not mark approved. `record` refuses an uncommitted package.
8. **QwenRAG adopts it deliberately** (see QwenRAG `docs/core-upgrade.md`): update the commit pin
   and `core-release.lock.json`, rebuild indexes if the index format or representation changed,
   run the adoption check and integration tests, review, merge, deploy.

Nothing is copied between repositories: QwenRAG installs the released package.

## Walkthrough: a hypothetical evidence-selection improvement

Suppose research finds that ordering parents by claim coverage before packing ("coverage-first")
reduces missing evidence.

1. It starts in `benchmark/track_b/policies.py` as a variant of `select`, evaluated in an offline
   replay — registry entry `track_b.E10_coverage_first`, status `experimental`, scope `component`.
2. The replay shows fewer missing anchors. That is a component result; the registry records it,
   with the replay's manifest hash as an artifact reference. QwenRAG is unaffected: its pinned
   core has no such code, and the registry is not part of any release.
3. To test it end to end, the strategy is implemented in the core (for example `Coverage.py`)
   behind a new `[rag_v2]` setting `evidence_order = "coverage_first"` whose default stays the
   current behavior. Research runs RAGFlow with the setting on, on the reserved questions, and
   stores `pipeline_identity.json` for each run.
4. A maintainer reviews per-question gains and losses, citation validity and answer quality,
   and marks the candidate `approved` with `released_in: "1.1.0"`.
5. The 1.1.0 release candidate sets `evidence_order = "coverage_first"` in the configuration used
   by `manifest`. The approved `pipeline_config_hash` now differs from 1.0.0 by exactly that field,
   and its evaluation evidence is the pipeline-scope run of that same configuration. The
   representation is unchanged, so `index_compatibility` stays the same and indexes are reused.
6. QwenRAG updates its pin to the 1.1.0 commit. `EngineSettings.from_release` takes the new
   setting from the package's `RELEASE.json`, so QwenRAG's own configuration does not change.
   The adoption check reports `approved_match`, and integration tests run.
7. If QwenRAG had instead set `evidence_order` locally without a release, its diagnostics would
   report `divergent` with the exact field, and startup would refuse unless
   `allow_divergent_pipeline` is set.

## Strategies that remain research-only

| Strategy | Where | Status | What promotion would need |
|---|---|---|---|
| E04 compact document identity (`identity_v2`) | `benchmark/track_b/representation.py` | experimental (component) | Core representation behind a setting with its own `REPRESENTATION_ID`; index rebuild procedure; pipeline-level answer evaluation on questions not used in development; review of C01/C09/S04 |
| E08 MMR selection | `benchmark/track_b/policies.py` | experimental, not superior to greedy | A new hypothesis with answer-level evaluation |
| E09 RRF / alternating ordering | `benchmark/track_b/policies.py` | experimental, mixed by budget | Runtime-need fusion after reliable needs and cost evaluation |
| E06 search strategies | design only | not implemented | Implementation and evaluation under the Track B protocol |
| Adaptive controller, directed and semantic retrieval, EvidenceSelection | `rag_ufc_core.rag.v2` (not wired) | experimental | Wiring into RAGFlow plus pipeline-level evaluation |

The current approved release, 1.0.0, has `release_kind = baseline_continuity`: it repackages the
production pipeline of `a998f73` and makes no new scientific claim.
