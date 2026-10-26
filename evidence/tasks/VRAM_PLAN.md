# VRAM Acceptance Plan

## Disk sizes (model-manifest.json)
- Raw model `Qwen3.8-27B-UD-IQ3_XXS.gguf`: 10934860704 bytes
- MTP `MTP/mtp-Qwen3.27B-Q4_0.gguf` (file `MTP/mtp-Qwen3.8-27B-Q4_0.gguf`): 1369590656 bytes
- Combined disk: 12304451360 bytes

These are disk byte counts, not measured runtime VRAM.

## Measured runtime delta (runtime-vram.json)
- Baseline host used: 1509 MiB; loaded host used: 15342 MiB
- Observed inference delta: 13833 MiB (14504951808 bytes)
- Caveat: delta includes runtime caches/buffers and possible desktop drift; not per-allocation accounting.

## Host snapshot (host-vram.json, older than runtime-vram.json)
host_total_mib=16303
host_used_mib=2005
host_free_mib=13991

Largest measured process consumers:

| Process | PID | Dedicated MiB |
|---|---|---|
| dwm | 195736 | 1688.2 |
| ChatGPT | 57080 | 368.7 |
| chrome | 311156 | 283.3 |

WDDM counters may overlap; do not sum as physical GPU usage. DWM is the desktop compositor; never terminate it.

## Safe reclamation after saving work
- Close unused browser tabs or disable browser hardware acceleration.
- Use a lower resolution or fewer active displays to reduce compositor surfaces.
- Offload inference weights or KV cache to RAM, at a measurable throughput cost.

## Verification (PowerShell)
```powershell
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits
```

Unmeasured facts (e.g., exact per-process physical GPU totals) are marked unknown.
