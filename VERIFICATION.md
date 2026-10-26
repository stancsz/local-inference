# Verified local workflow — 2026-10-26

Current follow-up: [native CLI stress campaign](docs/STRESS.md) is running against a frozen uncommitted newer Sift candidate. Its final acceptance is pending. The first accepted session has nine turns and 1040.878 active seconds; this does not establish the requested full 21-session outcome. Runtime/source and task receipts are being refreshed, so the historical baseline reconciliation below must not be read as final acceptance of that campaign. The latest host delta includes additional desktop occupancy; [stress memory snapshot](evidence/stress-runtime-vram.json) records a 14.44 GB host delta versus the older baseline and an unchanged main WSL dedicated counter of 13.80 GB, with overlapping-counter caveats.

The running product is an independent LiteLLM gateway at `127.0.0.1:8090` with mandatory CPU Sift compaction, backed by GPU llama.cpp. Its Docker network/configuration has no Subroute, cloud fallback, database, or Redis dependency. Development workers used Subroute separately; they are not product services.

## Recommended profile

RTX 5070 Ti; Qwen3.8-27B UD-IQ3_XXS plus Q4_0 MTP; all target/draft layers on GPU; q4 target/draft KV; one slot; 40,960 total context; 32,768 Sift anchor; 4,096 output limit; 256 decoder-headroom tokens; four draft tokens; microbatch 64. Thinking and context shifting are disabled. Sift budgets are now request-adaptive: histories above the anchor use `ceil(native_raw_tokens / 8)`, clamped to 24,576–65,536 and available input capacity. With full output reservation, the daily ceiling is 36,608; with 128 output tokens it is 40,576. This size policy does not classify task difficulty or measure free VRAM.

Start normal Claude work with `python scripts/claude_local.py`. The wrapper changes only its child environment and uses isolated local configuration.

## Evidence

| Check | Observed result | Receipt |
| --- | --- | --- |
| Model provenance | Two SHA256-verified artifacts; 12,304,451,360 combined disk bytes | [Manifest](evidence/model-manifest.json) |
| Sift regression after adaptive change | 553 passed, 1 skipped | [Suite](evidence/sift-suite.txt) |
| Budget and harness regressions | 38 passed, including 18 Sift dynamic tests and local budget, semantic artifact, fresh-download setup and usage checks | [Tests](evidence/adaptive-policy-tests.txt) |
| Native text, tool continuation and protected overflow | Text/tool continuation passed; oversized immutable current task rejected with HTTP 422 | [Smoke](evidence/local-smoke.json) |
| OpenAI adapter | Exact JSON-schema const; exact 16-token length stop; malformed system rejected with 422 | [Requests and responses](evidence/openai-smoke.json) |
| Three real Claude tasks | VRAM plan, model audit, adaptive operator runbook; native reads/edits, calculator for model-byte sum; successful exit; final accepted runs approximately 16–22 seconds | [CLI receipts](evidence/claude-acceptance.json) |
| Artifact integrity | Published SHA256s match reconstruction from successful native edits; required source reads preceded edits | [Artifacts](evidence/tasks), [parent review](evidence/acceptance-review.json) |
| 256k raw history | 257,539 native tokens; adaptive budget 32,193 → forwarded 32,053; evidence retained and answered correctly | [Context receipts](evidence/context-acceptance.json) |
| 1M raw history | 1,001,638 native tokens; adaptive budget 40,576 → forwarded 33,300; evidence retained and answered correctly | [Context receipts](evidence/context-acceptance.json) |
| Exact capacity | 65,536 input + 4,096 generated; no truncation | [Capacity receipt](evidence/capacity-64k-4k.json) |

Context receipts use one unchanged daily configuration and 128 output tokens; they prove differing chosen budgets as well as downstream limits. They correlate Sift count/selection inputs by SHA256, compare independent compaction with live gateway audit records, and reconcile native input counts with provider input plus cache-read usage. The digest is not a full provider-request or generation-output identity. Sift selection took approximately 1–3 seconds. The earlier [cold receipts](evidence/context-acceptance-cold.json) used the previous fixed-target policy and are historical comparisons, not current-policy acceptance. The unchanged optional 64k backend capacity receipt remains a separate capacity result; the larger-window adaptive policy is covered offline, not by a new 64k gateway replay.

## Performance and memory

The short 40k-profile benchmark measured about **103–104 decode tokens/s** with four draft tokens, versus about 92 with two. The matched 64k-window pair measured **91.18 with MTP versus 49.92 without**, a 1.83× decode ratio across two samples per arm. Outputs differed; these are microbenchmarks, not correctness-parity or general end-to-end productivity claims. See [paired summary](evidence/benchmark-summary.json), [two-draft](evidence/benchmark-mtp2-40k.json) and [four-draft](evidence/benchmark-mtp4-40k.json) receipts.

The recommended profile's observed host GPU delta ranged from approximately **13.62–13.83 decimal GB**, including runtime cache/buffer effects and desktop drift. A separate WSL VM dedicated-allocation counter was approximately **13.80 GB**. The [memory receipt](evidence/runtime-vram.json) records the actual values and caveats: host activity can drift, WDDM allocation counters can overlap, and neither is exact per-model physical allocation accounting. [Runtime source parity](evidence/runtime-source-parity.json) confirms the running app/Sift files match the inspected source and LiteLLM 1.106.4. Combined GGUF disk bytes are a separate measurement.

The optional 64k-input profile uses `CONTEXT_SIZE=69888`, `SIFT_TARGET=65536`, `DRAFT_TOKENS=2`. It passed exact 64k+4k generation, but its observed runtime delta with caches/buffers was slightly above 14 decimal GB. The daily default therefore favors the stricter memory target. The initial 69,632-token capacity trial stopped two tokens short; the added 256-token headroom corrected that boundary. This synthetic capacity test does not establish coherent 4k-output quality.

## Review and limits

Independent CLI reviews identified API edge cases, decoder headroom, and evidence/validator weaknesses. Concrete repairs were checked with live requests, boundary tests, exact artifact hashes, source snapshots, and source-field/command checks. The earlier review handoff had no clean final verdict. For this follow-up, exactly one write-enabled :4000/default CLI worker produced a partial policy change and exhausted its turn limit. Parent review found and repaired a bypass of pre-count size guards, completed tests/docs and directly verified the rebuilt :8090 path. The task key was deleted and its alias confirmed absent. [Adaptive review](evidence/adaptive-review.json) records commander acceptance and its limits.

The final **nonauthor review returned READY for the bounded local integration and published setup**: [review](evidence/integration-review.json). Its native CLI session inspected actual source/evidence and independently ran all 38 focused tests plus the live local/OpenAI smokes. It exhausted its turn limit before writing the verdict; one text-only API call on the same configured route completed the review from the full captured source/tool observations, without additional tools or product edits. This is not a clean successful CLI handoff or release-wide certification. Two nonblocking findings—an anchor-budget discontinuity and separate tool schemas outside message pre-count traversal bounds—are retained in [TECH_DEBT.md](TECH_DEBT.md). No runtime policy changes were made after that review. All review task keys were revoked and their aliases confirmed absent.

An initial unconstrained report guessed incorrect model sizes, and early harness attempts assumed a separate Write tool absent from this installed CLI. This follow-up also caught incorrect mental byte arithmetic and one copied process PID. The final model audit used a Python calculator; the VRAM report was narrowed to the three largest source consumers. A correct dictionary-shaped main/MTP mapping initially failed a string-only validator; the artifact was preserved and reaccepted after semantic validation, with wrong arithmetic/swapped mappings still rejected by tests. Failed attempts remain in ignored task scratch. These three accepted tasks do not prove broad model reliability. The long-history tests are synthetic retention probes and do not establish semantic equivalence or general retrieval accuracy.

Sift's original adapter was merged in [PR #57](https://github.com/stancsz/sift/pull/57); request-adaptive budgeting is merged in [PR #58](https://github.com/stancsz/sift/pull/58), commit `e62ed81d8fbf07b076a2cf5c8a9f94f61f509105`.

## Optional advisor and cloud-usage measurement

The [setup guide](docs/SETUP.md) documents a local-worker/strong-cloud-advisor pattern. `scripts/advisor.py` made one bounded text-only OpenAI-compatible call through the owner-configured :4000/default route; [receipt](evidence/advisor-example.json). That alias does not independently identify the upstream model. The advisor found no concrete issue in the supplied excerpt/evidence and explicitly limited its review; it did not replay tests or independently certify the integration.

The [usage example](evidence/usage-example.json) counts six local task attempts, including the rejected arithmetic/runbook/VRAM outputs, plus that one advisory review: 103,441 local tokens and 1,710 cloud-advisor tokens, or 1.63% cloud share. This mixed workload demonstrates accounting, not a paired advisor-assisted task experiment. It excludes development workers and has no equivalent cloud-only baseline. **No measured 99%+ cloud-token reduction or dollar saving is claimed.** The guide explains how to collect a comparable baseline and account for retries, cache tokens, quality and non-token costs.
