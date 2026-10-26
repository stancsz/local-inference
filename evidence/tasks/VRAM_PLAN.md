# VRAM Plan

## Disk byte counts (evidence/model-manifest.json)

- Raw model `Qwen3.8-27B-UD-IQ3_XXS.gguf`: 10934860704 bytes
- MTP `MTP/mtp-Qwen3.8-27B-Q4_0.gguf`: 1369590656 bytes
- Combined: 12304451360 bytes

These are disk sizes, not measured runtime GPU deltas.

## Measured runtime delta (evidence/runtime-vram.json)

- Baseline host used: 1509 MiB
- Loaded host used: 15252 MiB
- observed_inference_delta_mib: 13743
- observed_inference_delta_bytes: 14410579968

This delta is larger than the raw model disk size because it includes runtime caches/buffers and possible unrelated desktop drift; it is not per-allocation accounting.

## Host snapshot (evidence/host-vram.json, older snapshot)

host_total_mib=16303
host_used_mib=2005
host_free_mib=13991

Three largest measured process consumers:

| Process | PID | Dedicated MiB |
|---|---|---|
| dwm | 195736 | 1688.2 |
| ChatGPT | 57080 | 368.7 |
| chrome | 311156 | 283.3 |

## Safe VRAM reclamation after saving work

1. Close unused browser tabs or disable browser acceleration after saving work.
2. Use a lower resolution or fewer active displays to reduce compositor surfaces.
3. Inference can offload weights or KV cache to RAM, at a measurable throughput cost.

Never terminate DWM.

## Verification

```powershell
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits
```
