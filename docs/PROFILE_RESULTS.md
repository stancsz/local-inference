# Context, VRAM and throughput experiments

These are separate configuration experiments on this host, using the same Qwen IQ3_XXS target, MTP artifact named `Q4_0` and q4_0 KV caches. The embedded MTP tensor types are distinguished below. These experiments do not replace or increment the frozen long-session campaigns. Each experiment restored its captured runtime. The current daily launcher now shares the target's MTP weights; normal client approval settings are unchanged.

The memory limit used here is **14,000,000,000 bytes**, approximately **13,351.44 MiB**. This differs from 14 GiB. Each experiment samples whole-host GPU use about once per second and compares its largest sampled value against the **lower** stopped before/after baseline. Desktop drift and unsampled transients remain confounds; this is not isolated per-model residency.

| Epoch / settings | Decode measurement | Exact 65,536 input + 4,096 output | Conservative host delta | Native tasks |
| --- | --- | --- | --- | --- |
| v1: GPU layers 58, MTP 2, microbatch 64 | 4.69 tok/s sampled progress | Intentionally cancelled; 1,300 output tokens observed | 12,908 MiB / 13.535 GB | Not run |
| v2: all GPU, MTP 1, microbatch 32 | 72.45 tok/s short; 29.18 at full context | Passed, 259.523 s; no truncation, MTP active | 13,792 MiB / **14.462 GB** | 3/3 passed |
| v2: all GPU, MTP 1, microbatch 16 | 71.54 tok/s short; 29.12 at full context | Passed, 319.922 s; no truncation, MTP active | 13,536 MiB / **14.194 GB** | 2/3 passed |
| v3: four CPU weight blocks, GPU output head, MTP 1, microbatch 16 | 17.45 tok/s short | Not run: missed the predeclared 20-tok/s screening gate | 13,058 MiB / 13.692 GB | Not run |
| v5: all GPU, shared target/MTP weights, MTP 2, microbatch 32 | 90.51 tok/s short; 60.36 at full context | Passed, 188.390 s; no truncation, MTP active | 13,111 MiB / **13.748 GB** | 3/3 passed, no repairs |
| v4: unchanged v3 configuration; no benchmark rerun | Prior v3 measurement only | Failed the original 900-second HTTP deadline during prefill | 13,094 MiB / 13.730 GB | Not run after capacity failure |

The short decode figures average two sequential 256-token runs of the JSONL-parser prompt, one cold and one cached. They exclude prompt processing and Sift. The full-context figures come from synthetic repeated-log token IDs and forced 4,096-token generation; they do not establish coherent long-output quality. The v1 progress estimate uses sampled token-count differences and is not a comparable backend timing benchmark. v3's 20-tok/s screen remains failed; v4 evaluates a different question, capacity/task feasibility, without changing that outcome.

Both v2 configurations also passed the separate 256k/1M native-token compaction-retention checks, local text/tool continuation and OpenAI schema/output-limit smoke checks. The native tasks read actual repository evidence and produce a VRAM plan, manifest/default-configuration audit and daily-default runbook. They are not audits claiming that the running optional profile has the daily default's context size.

The microbatch-16 VRAM plan was rejected for missing `nvidia-smi`. Parent inspection also found an invalid `Get-Process.DedicatedMemory` verification expression. That property is absent on this host. A subsequent prompt/validator repair preserves the rejection and passes a fresh native VRAM task on the restored daily profile; see [the repair receipt](../evidence/gpu-verification-v1/receipt.json). No generated file was manually corrected.

A later [direct Windows VM-counter experiment](WINDOWS_GPU_ACCOUNTING.md) repeats the same shared-weight long profile and its native tasks. It records a13.485-GB dedicated-usage upper bound for the containing VM, including all counter aliases, with no desktop subtraction. That measurement is distinct from the whole-host deltas in the table. The [final read-only nonauthor review](../evidence/final-daily-driver-acceptance-v1.json) accepts the memory bound as MET_WITH_BOUNDS and the documented full local goal as READY. Earlier rejections are preserved.

## Reproduce the measurement analysis

```powershell
python scripts/profile_memory.py evidence/long-profile-v2/gpu-samples.jsonl --case 16
```

This independently replays the conservative calculation, checks case-label boundaries, distinguishes decimal bytes from GiB and reports effective sampling gaps. Missing baseline/case data fails closed. For example, v2 initially appeared below the limit using its 2,040-MiB starting baseline. Its final lower baseline was 1,674 MiB, changing the conservative result to 13,536 MiB. The report retains the stricter result.

The trace logs preserve individual CUDA model, KV, recurrent-state and compute-buffer sizes. Repeated reservation lines must not be summed as independent allocations or called a physical peak. Model weights, caches, driver/context overhead and unrelated desktop memory are different quantities.

## Shared-weight MTP

The main GGUF contains the nextn head (`qwen35.nextn_predict_layers=1`, block64). The pinned llama.cpp source explicitly creates an MTP context against the target model when a separate draft path is absent. v5 verified that startup log, no separate draft-model load, and accepted speculative tokens. This avoids the earlier 774.71-MiB separate CUDA draft-weight allocation. The original model files were not changed or requantized. Raw source excerpts, allocation logs, capacity, adaptive budget receipts, all native revisions and parent reconstruction are in the [v5 parent review](../evidence/long-profile-v5/parent-review.json). The main model CUDA buffer was 10,019.96 MiB; caches/state/compute are additional allocations. Repeated reservation lines must not be summed.

The stopped baseline ranged 1,669–1,910 MiB; sampled whole-host peak was 14,780 MiB. Subtracting the lower baseline gives 13,111 MiB, exactly 13,747,879,936 bytes. There were 382 valid case samples, no sample errors and a 1.357 s largest case gap. Desktop drift and shorter unsampled peaks remain limitations. The 1M history selected a 65,536-token budget and forwarded 33,300 tokens; the 256k history selected 32,193 and forwarded 32,053. Both retained the requested source fact. Capacity is a separate synthetic test, not a coherent 4k-output quality result.

## Evidence and remaining work

A later read-only [MTP quantization audit](../evidence/mtp-quantization-dryrun-v1/receipt.json) verified that the original artifact SHA256 is unchanged. Its filename says `Q4_0`, while its GGUF metadata declares file type14 (`Q4_K_S`) and the actual tensors mix Q3_K, Q4_K, Q6_K and F32. Filename-based model-audit tasks identify artifact labels; they do not establish every embedded tensor's precision. Original names and download manifests are retained for reproducibility.

The pinned image's quantizer estimates a 1,295.71-MiB source tensor payload, 1,216.13 MiB for pure Q3_K_S and 1,083.48 MiB for IQ3_XXS. These exclude GGUF metadata and are not VRAM savings: shared CPU-resident tensors also contribute to the file size. The IQ3_XXS dry run explicitly requires an importance matrix before actual quantization. No candidate was created or loaded; requantization quality and speculative acceptance remain untested.

- [v1 cancelled trial and parent replay](../evidence/long-profile-v1/parent-review.json)
- [v2 positive and negative artifacts, native reconstruction and memory replay](../evidence/long-profile-v2/parent-review.json)
- [v3 gate failure](../evidence/long-profile-v3/parent-review.json) and [independent restoration check](../evidence/long-profile-v3/parent-restoration-check.json)
- [v4 timeout and restored runtime](../evidence/long-profile-v4/parent-review.json)

v3's raw restoration assertion reported a mismatch between equivalent `C:\...` and `/run/desktop/mnt/host/c/...` bind paths. Independent checks confirmed the same read-only source, startup bytes, image IDs, environment settings and 40k native window, followed by passing local/OpenAI smokes. The original assertion failure remains preserved; v4 checks canonical aliases and startup bytes directly.

**v5 passes the sampled conservative 14-decimal-GB host-delta criterion, exact 64k+4k completion and the three native tasks. Isolated per-allocation residency remains unverified.** The earlier separate-draft fully GPU configurations complete the work but miss the conservative memory criterion. CPU offload reduces sampled memory but exposes prefill/decode costs on the current CPU setup. This is a measured configuration/backend tradeoff, not evidence that Sift caused a generation error or that the combination is mathematically impossible.

The backend warns that CPU tensor overrides with mmap may perform better with `--load-mode none`. That is an untested, concrete next prefill probe; another long capacity run should first be justified by a small task-shaped latency measurement. The existing 40k fast default remains available. Codex nine-turn coverage, the per-client qualification gate and final full-goal independent acceptance remain open. These profile experiments increment qualification by zero. A later separately sealed Codex session brings parent-qualified candidate totals to Claude 8 / OpenCode 9 / Codex 7; see docs/STRESS_RESULTS.md.
