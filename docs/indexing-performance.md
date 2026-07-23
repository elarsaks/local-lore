# Indexing performance investigation

Measured on 2026-07-23 on Darwin arm64 with Docker Desktop 29.6.1. All
production-model measurements ran with `network_mode: none`; the fixture and
model were local.

## Method

`benchmarks/profile_indexing.py` creates deterministic JSONL histories and
measures discovery, initial import, unchanged import, append-only import, and
embedding writes independently:

```bash
uv run python benchmarks/profile_indexing.py \
  --files 1000 --messages-per-file 10 --changed-files 100
```

The database-focused results below are medians of three sequential runs. The
embedder in this benchmark is deterministic and intentionally cheap so that
SQLite and importer costs remain visible. Production measurements used
separate Docker images for the unmodified revision and this change, isolated
named volumes, the bundled BGE model, and the same 1,000-file fixture.

## Findings

The major costs are:

1. **Embedding model work.** A full import of roughly 10,000 messages took
   21–22 seconds end to end with either image. The database-only initial import
   was about 1.1–1.4 seconds, so production embedding inference dominates a
   large cold build. Deferring embeddings would improve readiness further, but
   it would temporarily change hybrid-search completeness and was not done.
2. **Unconditional model initialization and asset hashing.** The old indexer
   loaded ONNX even when every embedding was current. It also hashed every
   model asset on each process start. Hashing a representative 177 MB local
   asset tree took 13.86 seconds outside the container. In the controlled
   container test, avoiding those operations removed about 0.52 seconds from
   an unchanged startup.
3. **SQLite statement and transaction overhead.** A cProfile run over 10,000
   records attributed 0.221 of 0.462 profiled import seconds to
   `sqlite3.Connection.execute`; JSON decoding and record parsing used about
   0.045 seconds. The previous importer also committed once per changed file
   and queried each checkpoint twice.
4. **File discovery is a bounded fixed cost.** Walking, resolving, sorting, and
   statting 1,000 files took about 0.055 seconds. It dominates the pure
   unchanged importer after model initialization is removed, but is not the
   leading cost when new messages require embeddings.
5. **Container creation is not the bottleneck.** A bare `/bin/true` in the
   production image took about 0.03 seconds. Most observed startup time is
   Python application and model work rather than Docker container creation.

FTS5 updates are included in the SQLite timings because the messages table
maintains FTS through triggers. They were not disabled for a separate timing:
doing so would no longer represent production correctness.

## Changes

- Import checkpoints are loaded once and passed into the file importer.
- All changed files in one indexing pass share a transaction. A failure rolls
  back messages and checkpoints together, preserving deterministic restart
  behavior.
- Repeated session upserts are skipped while the project and working-directory
  metadata remain unchanged.
- The content-derived model checksum is computed during the image build and
  stored with the immutable bundled assets. Custom model directories without a
  checksum retain the full runtime hashing fallback.
- The indexer checks for pending or stale embeddings before constructing the
  model. Model changes still cause re-embedding because the pending check uses
  the model name, content checksum, dimension, and message content hash.

No network access, nondeterministic parallel writes, or mtime-only model
identity was introduced.

## Results

Database-focused synthetic import:

| Workload | Before | After | Change |
| --- | ---: | ---: | ---: |
| Initial: 10,000 messages / 1,000 files | 1.422 s | 1.116 s | 21.5% faster |
| Unchanged: 1,000 files | 0.059 s | 0.056 s | 6.1% faster |
| Incremental: 100 appends / 100 files | 0.225 s | 0.196 s | 12.7% faster |

End-to-end Docker run with the production embedding model:

| Workload | Before | After | Change |
| --- | ---: | ---: | ---: |
| Unchanged 1,000-file index | 1.515 s | 0.991 s | 34.6% faster |
| 100 new messages in 100 files | 1.772 s | 1.637 s | 7.6% faster |

The cold full-index measurements were approximately 21–22 seconds with no
reliable improvement; embedding throughput dominates that workload. The
implemented changes target the reported incremental startup path, while the
benchmark makes a future embedding-throughput or safe background-indexing
change measurable.
