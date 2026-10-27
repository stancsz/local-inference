# Context, VRAM and throughput experiments

These are separate configuration experiments on this host, using the same Qwen IQ3_XXS target, Q4_0 MTP and q4_0 KV caches. They do not replace or increment the frozen long-session campaigns. The original 40,960-token daily profile is restored with its original images/settings; normal client approval settings are unchanged.

The memory limit used here is **14,000,000,000 bytes**, approximately **13,351.44 MiB**. This differs from 14 GiB. Each experiment samples whole-host GPU use about once per second and compares its largest sampled value against the **lower** stopped before/after baseline. Desktop drift and unsampled transients remain confounds; this is not isolated per-model residency.

| Epoch / settings | Decode measurement | Exact 65,536 input + 4,096 output | Conservative host delta | Native tasks |
| --- | --- | --- | --- | --- |
| v1: GPU layers 58, MTP 2, microbatch 64 | 4.69 tok/s sampled progress | Intentionally cancelled; 1,300 output tokens observed | 12,908 MiB / 13.535 GB | Not run |
| v2: all GPU, MTP 1, microbatch 32 | 72.45 tok/s short; 29.18 at full context | Passed, 259.523 s; no truncation, MTP active | 13,792 MiB / **14.462 GB** | 3/3 passed |
| v2: all GPU, MTP 1, microbatch 16 | 71.54 tok/s short; 29.12 at full context | Passed, 319.922 s; no truncation, MTP active | 13,536 MiB / **14.194 GB** | 2/3 passed |
| v3: four CPU weight blocks, GPU output head, MTP 1, microbatch 16 | 17.45 tok/s short | Not run: missed the predeclared 20-tok/s screening gate | 13,058 MiB / 13.692 GB | Not run |
| v4: unchanged v3 configuration; no benchmark rerun | Prior v3 measurement only | Failed the original 900-second HTTP deadline during prefill | 13,094 MiB / 13.730 GB | Not run after capacity failure |

The short decode figures average two sequential 256-token runs of the JSONL-parser prompt, one cold and one cached. They exclude prompt processing and Sift. The full-context figures come from synthetic repeated-log token IDs and forced 4,096-token generation; they do not establish coherent long-output quality. The v1 progress estimate uses sampled token-count differences and is not a comparable backend timing benchmark. v3's 20-tok/s screen remains failed; v4 evaluates a different question, capacity/task feasibility, without changing that outcome.

Both v2 configurations also passed the separate 256k/1M native-token compaction-retention checks, local text/tool continuation and OpenAI schema/output-limit smoke checks. The native tasks read actual repository evidence and produce a VRAM plan, manifest/default-configuration audit and daily-default runbook. They are not audits claiming that the running optional profile has the daily default's context size.

The microbatch-16 VRAM plan was rejected for missing `nvidia-smi`. Parent inspection also found an invalid `Get-Process.DedicatedMemory` verification expression. That property is absent on this host. A subsequent prompt/validator repair preserves the rejection and passes a fresh native VRAM task on the restored daily profile; see [the repair receipt](../evidence/gpu-verification-v1/receipt.json). No generated file was manually corrected.

## Reproduce the measurement analysis

```powershell
python scripts/profile_memory.py evidence/long-profile-v2/gpu-samples.jsonl --case 16
```

This independently replays the conservative calculation, checks case-label boundaries, distinguishes decimal bytes from GiB and reports effective sampling gaps. Missing baseline/case data fails closed. For example, v2 initially appeared below the limit using its 2,040-MiB starting baseline. Its final lower baseline was 1,674 MiB, changing the conservative result to 13,536 MiB. The report retains the stricter result.

The trace logs preserve individual CUDA model, KV, recurrent-state and compute-buffer sizes. Repeated reservation lines must not be summed as independent allocations or called a physical peak. Model weights, caches, driver/context overhead and unrelated desktop memory are different quantities.

## Evidence and remaining work

- [v1 cancelled trial and parent replay](../evidence/long-profile-v1/parent-review.json)
- [v2 positive and negative artifacts, native reconstruction and memory replay](../evidence/long-profile-v2/parent-review.json)
- [v3 gate failure](../evidence/long-profile-v3/parent-review.json) and [independent restoration check](../evidence/long-profile-v3/parent-restoration-check.json)
- [v4 timeout and restored runtime](../evidence/long-profile-v4/parent-review.json)

v3's raw restoration assertion reported a mismatch between equivalent `C:\...` and `/run/desktop/mnt/host/c/...` bind paths. Independent checks confirmed the same read-only source, startup bytes, image IDs, environment settings and 40k native window, followed by passing local/OpenAI smokes. The original assertion failure remains preserved; v4 checks canonical aliases and startup bytes directly.

**No tested configuration here establishes the simultaneous strict 14-decimal-GB bound, exact 64k+4k completion within the original deadline and productive native task acceptance.** The faster fully GPU configurations complete the work but miss the conservative memory criterion. CPU offload reduces sampled memory but exposes prefill/decode costs on the current CPU setup. This is a measured configuration/backend tradeoff, not evidence that Sift caused a generation error or that the combination is mathematically impossible.

The backend warns that CPU tensor overrides with mmap may perform better with `--load-mode none`. That is an untested, concrete next prefill probe; another long capacity run should first be justified by a small task-shaped latency measurement. The existing 40k fast default remains available. Codex nine-turn coverage, the per-client qualification gate and final full-goal independent acceptance remain open. Candidate totals stay Claude 8 / OpenCode 9 / Codex 6; all experiments here increment qualification by zero.
