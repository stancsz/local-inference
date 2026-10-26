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
Verified: Sift dynamic adapter merged via PR #57 (89c8916), 547 offline tests passed/1 skipped; 11 local budget tests passed. Both model artifacts SHA256 verified. Standalone LiteLLM has live text and native tool continuation receipts. Raw 257,539 and 1,001,638 native tokens compacted to 32,689 and 32,648 with source retention, matching live audit/provider counts. Three final 40k-profile Claude artifacts passed source-field, command, length and arithmetic checks, native-edit reconstruction, and parent factual review. Earlier wrong values and harness assumptions are retained as failed-attempt history, not accepted results.

Completed: exact 65,536 input + 4,096 generated without truncation; native OpenAI schema/cap/invalid-system checks; 11 local budget tests; three corrected Claude artifacts with source snapshots and native-edit SHA256 binding; cold and cached 256k/1M context receipts. Four-draft 40k profile measured ~103–104 short-prompt decode tokens/s. Matched 64k-window MTP/no-MTP pair measured 91.18/49.92 tokens/s (1.83x). Recommended 40k/32k Sift profile observed ~13.62–13.83 decimal GB host GPU delta, with separate WSL allocation counters below 14 GB.

Acceptance: the user's permitted productive-profile alternative is selected. The optional 64k+4k capacity profile works but uses slightly over 14 decimal GB including cache/buffers. Do not claim all constraints simultaneously at 64k. Independent reviews were performed and concrete findings repaired; the final read-only handoff hit its bounded budget, so no clean final independent PASS is claimed. Commander acceptance is limited to the live local workflow and three actual artifacts, not broad model reliability. See VERIFICATION.md for the full reconciliation.

Remaining for this bounded delivery: final scoped commit/push and clean-state verification. No required runtime experiment remains. Later broad quality evaluation and release-wide QA are outside this accepted increment. Runtime source parity matches the inspected app and Sift source; implementation-only Subroute worker/review helpers were removed from the product tree and preserved in ignored scratch.

Environment: empty remote fetched on 2026-10-26. RTX 5070 Ti, 16,303 MiB; ~48 GiB system RAM. Initial host occupancy 4,018 MiB, reduced by user/parallel host work to a measured pre-inference baseline of 1,509 MiB. Existing active Codex goal owns the full request. User/other-task VRAM scripts and receipts are preserved without staging them.

## Ownership and authority
Codex parent is the accepting commander. CLI workers use the local LiteLLM :4000 default route; final acceptance uses the requested local model path. User authorizes experiments, changes in both projects, Docker setup, scoped commits and pushes. Preserve unrelated work and existing services.
