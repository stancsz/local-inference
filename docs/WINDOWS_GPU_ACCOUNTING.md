# Windows GPU accounting

The first full-goal reviewer rejected a whole-host before/after delta as proof of model+MTP residency. That [NOT_READY verdict](../evidence/final-goal-review-v1.json) remains unchanged.

The [separately sealed VM-counter experiment](../evidence/vm-residency-v1-plan.json) measures Windows GPU Process Memory counters for every `vmwp` process and instance. Microsoft's GPU memory manager supplies these counters. Per-process values include private and cross-process shared resources, so sums can overcount physical memory. See [Microsoft's definitions](https://devblogs.microsoft.com/directx/gpus-in-the-task-manager/).

The proposed inference is an upper bound: the Docker/WSL model and MTP allocations are contained in the VM's GPU usage. Including other VM resources and every counter alias makes that bound conservative. **No desktop baseline is subtracted.** This is not an exact isolated-model value; independent acceptance of the inference is required.

| Measurement | Result |
| --- | ---: |
| Peak summed VM dedicated usage | 13,485,330,432 bytes / 13.485 GB |
| Peak summed GPU-related committed usage, including shared system memory | 13,616,123,904 bytes / 13.616 GB |
| Stopped VM dedicated usage, before and after | 24,059,904 bytes |
| Case samples / largest gap | 435 / 2.599 seconds |
| Sampling errors | 0 |
| Limit | 14,000,000,000 bytes |

The same fully GPU shared-MTP profile completed exact65,536 input +4,096 output, both256k/1M retention checks and three native Claude tasks. The runbook required one bounded feedback repair; its failed revision is preserved. Original image, environment, mounts and startup bytes were restored, followed by passing local/OpenAI checks. [Parent replay and raw evidence](../evidence/vm-residency-v1/parent-review.json) retain the allocation logs, counters and native artifacts.

Reproduce analysis with:

```powershell
python scripts/profile_memory.py evidence/vm-residency-v1/vm-counters.jsonl --case 32 --scope vm
```

Missing counters, unmatched process identities, duplicate instance names, invalid bytes, missing stopped controls, insufficient load change or a gap beyond the predeclared five seconds fail closed. Distinct aliases remain in the sum.

Limitations: [NVIDIA does not expose per-process GPU memory under WDDM](https://docs.nvidia.com/deploy/nvidia-smi/index.html#processes). Direct kernel process-query access was denied to this nonadmin executor; no elevation or permission change was attempted. [Microsoft documents counter overreporting on affected Windows systems](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/gpu-process-memory-counters-report-wrong-value). Sampling does not establish a continuous-time peak, and no universal workload bound or exact per-container residency is claimed. Host occupancy, VM dedicated usage and individual CUDA allocation sizes remain separate quantities.
