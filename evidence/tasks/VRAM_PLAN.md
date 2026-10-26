# VRAM Plan

## Disk sizes (model-manifest.json)
- Raw model `Qwen3.8-27B-UD-IQ3_XXS.gguf`: 10,934,860,704 bytes
- MTP `MTP/mtp-Qwen3.8-27B-Q4_0.gguf`: 1,369,590,656 bytes
- Combined disk bytes: 12,304,451,360

## Measured runtime delta (runtime-vram.json)
- Baseline host used: 1509 MiB
- Loaded host used: 14661 MiB
- Observed inference delta: 13152 MiB (13,790,871,552 bytes)
- Caveat: host delta includes runtime caches/buffers and possible desktop drift; not per-allocation accounting.

Disk size (12,304,451,360 bytes) is not the same as the measured runtime delta (13,790,871,552 bytes). The delta includes KV cache, runtime buffers, and WSL overhead beyond raw weights.

## Host snapshot (host-vram.json, 2026-10-26T19:00:03Z)
This is the older host snapshot, distinct from runtime-vram.json (2026-10-26T20:52:53Z).

host_total_mib=16303
host_used_mib=2005
host_free_mib=13991

### Top three measured process consumers (host-vram.json)

| Process | PID | Dedicated MiB |
|---------|-----|---------------|
| dwm | 195736 | 1688.2 |
| ChatGPT | 57080 | 368.7 |
| chrome | 311156 | 283.3 |

## Safe VRAM reclamation (after saving work)
1. Close unused browser tabs (chrome 283.3 MiB).
2. Disable browser hardware acceleration.
3. Lower display resolution or reduce active displays to shrink compositor surfaces.
4. Close optional GPU apps (e.g., ChatGPT 368.7 MiB) if not in use.
5. Never terminate DWM (PID 195736, 1688.2 MiB) — it is the desktop compositor.
6. Optionally offload inference weights or KV cache to RAM at a measurable throughput cost.

## Verification (PowerShell)
```powershell
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader
```
Confirm total/used/free order matches host-vram.json GPU line.