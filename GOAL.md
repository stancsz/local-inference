# Productive local inference with Sift

## Ask
Run Qwen3.8 27B, 3/4-bit quantization and MTP, in Docker on this Windows host. Sift is a mandatory CPU compaction prerequisite for 256k-1M working histories, forwarding a dynamic 24k-64k working set. Commit and push scoped milestones in both repositories.

User clarification: this is its own clean minimal LiteLLM gateway, independent of Subroute. Runtime has only gateway + inference containers; no shared routing database, cloud fallback or :4000 dependency. Build/review workers may use the standing :4000 delegation route, but product acceptance must use :8090 local Qwen.

## Acceptance
- Measured model + MTP GPU residency below 14 GB; separately report total host VRAM and cache/compute memory.
- Prefer 65,536 input tokens plus 4,096 output tokens; benchmark a smaller productive profile if required, retaining the long-context result explicitly.
- Measure prefill/decode speed and MTP enabled/disabled behavior with reproducible receipts.
- Protect system/current request and complete tool call/result groups; fail closed if mandatory content cannot fit.
- Exercise 256k and 1M histories through real Sift compaction with retention checks and downstream limits.
- Three real Claude Code CLI productivity/engineering tasks against the local inference + Sift path, native tool events, exit status and independently checked artifacts.
- Independent review of cross-component integration; reproducible setup, limitations and evidence linked from README.

## Remaining
Verified: Sift dynamic adapter merged via PR #57 (89c8916), 547 offline tests passed/1 skipped; 6 local budget tests passed. Both model artifacts SHA256 verified. Standalone LiteLLM has live text and native tool continuation receipts. Raw 257,539 and 1,001,638 native tokens compacted to 32,689 and 32,648 with source retention, matching live audit/provider counts. Three 40k-profile Claude tasks completed native edits; parent found one swapped used/free number in the VRAM narrative and is tightening source-field validation before final acceptance.

Remaining: exact 64k+4k capacity, paired MTP/no-MTP metrics, strict decimal-GB memory profile selection, final corrected Claude task run, current-source independent review, documentation and final push. The 64k runtime's observed host delta is slightly above 14 decimal GB including cache/buffers; the 40k profile was below it. The full ask is not yet accepted.

Environment: empty remote fetched on 2026-10-26. RTX 5070 Ti, 16,303 MiB; ~48 GiB system RAM. Initial host occupancy 4,018 MiB, reduced by user/parallel host work to a measured pre-inference baseline of 1,509 MiB. Existing active Codex goal owns the full request. User/other-task VRAM scripts and receipts are preserved without staging them.

## Ownership and authority
Codex parent is the accepting commander. CLI workers use the local LiteLLM :4000 default route; final acceptance uses the requested local model path. User authorizes experiments, changes in both projects, Docker setup, scoped commits and pushes. Preserve unrelated work and existing services.
