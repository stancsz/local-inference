# VRAM Plan

## Disk sizes (model-manifest.json)
- Raw model `Qwen3.8-27B-UD-IQ3_XXS.gguf`: 10934860704 bytes (IQ3_XXS, 3.0625 bpw)
- MTP `MTP/mtp-Qwen3.8-27B-Q4_0.gguf`: 1369590656 bytes (Q4_0)
- Combined disk bytes: 12304451360

These are on-disk file sizes from the manifest, not measured VRAM.

## Measured runtime delta (runtime-vram.json)
- baseline_host_used_mib: 1509
- loaded_host_used_mib: 14493
- observed_inference_delta_mib: 12984 (13614710784 bytes)

This is a host-level delta including runtime caches/buffers and possible
desktop drift; it is not per-allocation accounting and does not equal the
manifest disk byte count.

## Host snapshot (host-vram.json, older than runtime-vram.json)
GPU: NVIDIA GeForce RTX 5070 Ti

host_total_mib=16303
host_used_mib=2005
host_free_mib=13991

Measured process consumers (dedicated_mib, host-vram.json):
- dwm (pid 195736): 1688.2
- ChatGPT (pid 57080): 368.7
- chrome (pid 311156): 283.3
- explorer (pid 8780): 231.5
- WeChatAppEx (pid 201224): 218.5
- csrss (pid 1144): 166.8
- Spotify (pid 225056): 45.6
- WindowsTerminal (pid 37576): 42.9

DWM is the desktop compositor; never terminate it. WDDM process counters
may overlap and must not be summed as physical GPU usage.

## Safe VRAM reclamation (after saving work)
1. Close unused browser tabs or disable browser hardware acceleration.
2. Lower display resolution or reduce active displays to shrink compositor
   surfaces.
3. Optionally offload weights or KV cache to RAM, accepting a measurable
   throughput cost.

## Verification (PowerShell)
```powershell
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits
```

Unmeasured facts: per-process live VRAM at runtime capture time is unknown.
