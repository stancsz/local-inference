# Verified local workflow — 2026-10-26

The running product is an independent LiteLLM gateway at `127.0.0.1:8090` with mandatory CPU Sift compaction, backed by GPU llama.cpp. Its Docker network/configuration has no Subroute, cloud fallback, database, or Redis dependency. Development workers used Subroute separately; they are not product services.

## Recommended profile

RTX 5070 Ti; Qwen3.8-27B UD-IQ3_XXS plus Q4_0 MTP; all target/draft layers on GPU; q4 target/draft KV; one slot; 40,960 total context; 32,768 native Sift input target; 4,096 output limit; 256 decoder-headroom tokens; four draft tokens; microbatch 64. Thinking and context shifting are disabled.

Start normal Claude work with `python scripts/claude_local.py`. The wrapper changes only its child environment and uses isolated local configuration.

## Evidence

| Check | Observed result | Receipt |
| --- | --- | --- |
| Model provenance | Two SHA256-verified artifacts; 12,304,451,360 combined disk bytes | [Manifest](evidence/model-manifest.json) |
| Sift baseline/regression | 547 passed, 1 skipped | [Suite](evidence/sift-suite.txt) |
| Local budget/edge cases | 11 passed | [Tests](evidence/proxy-tests.txt) |
| Native text and tool continuation | Passed through the local gateway | [Smoke](evidence/local-smoke.json) |
| OpenAI adapter | Exact JSON-schema const; exact 16-token length stop; malformed system rejected with 422 | [Requests and responses](evidence/openai-smoke.json) |
| Three real Claude tasks | VRAM plan, model audit, operator runbook; native reads/edits; successful exit; about 15 seconds each in final accepted runs | [CLI receipts](evidence/claude-acceptance.json) |
| Artifact integrity | Published SHA256s match reconstruction from successful native edits; required source reads preceded edits | [Artifacts](evidence/tasks), [parent review](evidence/acceptance-review.json) |
| 256k raw history | 257,539 native tokens → 32,689; evidence retained and answered correctly | [Context receipts](evidence/context-acceptance.json) |
| 1M raw history | 1,001,638 native tokens → 32,648; evidence retained and answered correctly | [Context receipts](evidence/context-acceptance.json) |
| Exact capacity | 65,536 input + 4,096 generated; no truncation | [Capacity receipt](evidence/capacity-64k-4k.json) |

Context receipts correlate Sift count/selection inputs by SHA256, compare independent compaction with live gateway audit records, and reconcile native input counts with provider input plus cache-read usage. The digest is not a full provider-request or generation-output identity. Sift selection took approximately 1–3 seconds. Current repeated probes benefit from prefix caching; [earlier cold receipts](evidence/context-acceptance-cold.json) retain the uncached comparison.

## Performance and memory

The short 40k-profile benchmark measured about **103–104 decode tokens/s** with four draft tokens, versus about 92 with two. The matched 64k-window pair measured **91.18 with MTP versus 49.92 without**, a 1.83× decode ratio across two samples per arm. Outputs differed; these are microbenchmarks, not correctness-parity or general end-to-end productivity claims. See [paired summary](evidence/benchmark-summary.json), [two-draft](evidence/benchmark-mtp2-40k.json) and [four-draft](evidence/benchmark-mtp4-40k.json) receipts.

The recommended profile's observed host GPU delta ranged from approximately **13.62–13.83 decimal GB**, including runtime cache/buffer effects and desktop drift. A separate WSL VM dedicated-allocation counter was approximately **13.80 GB**. The [memory receipt](evidence/runtime-vram.json) records the actual values and caveats: host activity can drift, WDDM allocation counters can overlap, and neither is exact per-model physical allocation accounting. [Runtime source parity](evidence/runtime-source-parity.json) confirms the running app/Sift files match the inspected source and LiteLLM 1.106.4. Combined GGUF disk bytes are a separate measurement.

The optional 64k-input profile uses `CONTEXT_SIZE=69888`, `SIFT_TARGET=65536`, `DRAFT_TOKENS=2`. It passed exact 64k+4k generation, but its observed runtime delta with caches/buffers was slightly above 14 decimal GB. The daily default therefore favors the stricter memory target. The initial 69,632-token capacity trial stopped two tokens short; the added 256-token headroom corrected that boundary. This synthetic capacity test does not establish coherent 4k-output quality.

## Review and limits

Independent CLI reviews identified API edge cases, decoder headroom, and evidence/validator weaknesses. Concrete repairs were checked with live requests, boundary tests, exact artifact hashes, source snapshots, and source-field/command checks. The final read-only review handoff hit its bounded budget; **no clean final independent PASS is claimed**. The commander accepts the bounded local workflow from the attached evidence; this is not release-wide certification.

An initial unconstrained report guessed incorrect model sizes, and early harness attempts assumed a separate Write tool absent from this installed CLI. The corrected harness uses Read/Edit, source-based constraints, and fail conditions; failed attempts remain in ignored task scratch. These three accepted tasks do not prove broad model reliability. The long-history tests are synthetic retention probes and do not establish semantic equivalence or general retrieval accuracy.

Sift's dynamic adapter was merged in [Sift PR #57](https://github.com/stancsz/sift/pull/57), commit `89c891640bc2647012d9eef9762571a13d1e04b5`.
