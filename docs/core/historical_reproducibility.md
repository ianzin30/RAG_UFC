# Historical reproducibility across the core extraction

The core extraction does not rewrite any experimental record. Results under
`benchmark/results/` (outside Git) keep the identities they were produced with.

## What still verifies after the extraction

* Frozen-source comparisons by path (Track B `load_source` reads
  `application/service/rag/v2/{EvidenceSelection,Dense,Retrieval,Models,OllamaEmbeddings}.py`):
  those paths are symlinks to byte-identical package files.
* `code.zip` archives and `reproducibility.code_files()` still include the legacy paths;
  `code_files()` now also includes `packages/rag-ufc-core/src`, so implementation hashes of
  *new* runs differ from pre-extraction runs (they describe different file sets).
* Historical configurations: `python -m benchmark.promotion config-identity --code-zip
  <run>/code.zip --llm-section benchmark.llm` gives the configuration identity of any archived
  run, comparable with a release (`--compare-release`).

## What intentionally fails after the extraction

Some packages record SHA-256 of protected inputs by **absolute path**, including engine files
(`protected_before.json`, `manifest.json` inputs in `benchmark/results/track_b/*`), and resume
checks compare the current `implementation_hash()` with the stored one. Engine files that changed
(`Engine.py`, `Config.py`, `Spark.py`, `Collections.py`, `RuntimeConfig.py`, `llm_client.py`, …)
therefore fail those checks: the protected inputs did change. This is correct and is not relaxed.

Also independent of the extraction: `benchmark/track_b/gemma_counter.py` keys its verification
record by the absolute path of the checkout (`/Users/…/RAG_UFC/…`), so any checkout at another
path fails those checks, with or without the extraction.

## Resuming a session started before the extraction

Use the pre-extraction code in the original location:

```bash
git -C /Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC switch --detach research-pre-core-extraction-2026-10-21
# …continue the session (results/ and data/ are outside Git and unaffected)…
git -C /Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC switch -
```

The tag `research-pre-core-extraction-2026-10-21` marks commit `a998f73`, the last commit before
the extraction. The uncommitted Track A/B work of that date is preserved byte-for-byte in the
`migration/research-integration` branch (commit "snapshot in-progress Track A/B work") and in
`~/Desktop/RAG-UFC/migration-backups/rag_ufc_wip_2026-10-21.tgz`.

New sessions started after the extraction record the new file set and verify normally.

## Mapping old files to new ones

`releases/rag-ufc-core/1.0.0.lineage.json` maps each moved file (old path → package path) with
its hash at `a998f73` and now. Byte-identical files carry the same algorithm; the six changed
files only remove checkout coupling, as described in the 1.0.0 release manifest.
