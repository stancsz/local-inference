# Productive local inference with Sift

## Ask
Run Qwen3.8 27B, 3/4-bit quantization and MTP, in Docker on this Windows host. Sift is a mandatory CPU compaction prerequisite for 256k-1M working histories, forwarding a dynamic 24k-64k working set. Commit and push scoped milestones in both repositories.

## Acceptance
- Measured model + MTP GPU residency below 14 GB; separately report total host VRAM and cache/compute memory.
- Prefer 65,536 input tokens plus 4,096 output tokens; benchmark a smaller productive profile if required, retaining the long-context result explicitly.
- Measure prefill/decode speed and MTP enabled/disabled behavior with reproducible receipts.
- Protect system/current request and complete tool call/result groups; fail closed if mandatory content cannot fit.
- Exercise 256k and 1M histories through real Sift compaction with retention checks and downstream limits.
- Three real Claude Code CLI productivity/engineering tasks against the local inference + Sift path, native tool events, exit status and independently checked artifacts.
- Independent review of cross-component integration; reproducible setup, limitations and evidence linked from README.

## Remaining
All runtime and task acceptance is unverified. Empty remote fetched on 2026-10-26. Host: RTX 5070 Ti, 16,303 MiB, initial total occupancy 4,018 MiB; ~48 GiB system RAM. Existing active Codex goal owns the full request.

## Ownership and authority
Codex parent is the accepting commander. CLI workers use the local LiteLLM :4000 default route; final acceptance uses the requested local model path. User authorizes experiments, changes in both projects, Docker setup, scoped commits and pushes. Preserve unrelated work and existing services.
