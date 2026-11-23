# Local Inference: market position and maturity

**Reviewed:** 2026-11-23<br>
**Product readiness:** single-host research prototype / supervised pilot. The documented workflow runs on one RTX 5070 Ti host; the evidence does not establish a broadly supported product.<br>
**Market validation:** hypothesis. No representative customer interviews, independent repeat-use cohort, paid usage, or willingness-to-pay evidence is published.

## Audience and job

The intended user is a developer who has a supported local GPU, can operate Docker and model files, and wants coding-agent inference and tool loops to stay on a workstation. The job is to make local inference usable through familiar client APIs, keep optional cloud judgment explicit, and retain receipts for speed, capacity, context, and task checks.

## Alternatives and position

| Substitute | What its first-party material establishes | Local Inference's testable position |
| --- | --- | --- |
| LM Studio local server | A local model server with OpenAI- and Anthropic-compatible endpoints, including tool use. | This repository offers a pinned, code-first LiteLLM/llama.cpp configuration, an explicit Sift callback, and a tested Claude Code workflow for one documented Windows GPU. No head-to-head usability or quality advantage is measured. |
| Cloud coding models and hosted agent tools | Avoid local GPU ownership and model-download/setup work. | Local token-heavy work can remain on owned hardware, with a deliberately separate optional advisor. The user pays in hardware, setup time, throughput, and model-quality trade-offs. |
| Other local serving stacks | Users can assemble their own model server, client, and context-management components. | The project packages a bounded, reproducible configuration and publishes its failures and resource receipts. General portability is not established. |

Local servers and compatible endpoints are established alternatives: [LM Studio local API server](https://lmstudio.ai/docs/developer/core/server), [LM Studio tool use](https://lmstudio.ai/docs/developer/openai-compat/tools), and [LM Studio offline operation](https://lmstudio.ai/docs/app/offline). These sources describe LM Studio's own product; they do not demonstrate a comparison with this repository.

## Evidence and limits

- The README and [verification record](../VERIFICATION.md) report one host configuration, reproducible benchmark receipts, capacity and context probes, and bounded Claude Code tasks.
- The matched shared-weight MTP decode comparison reports a 102.75 tok/s mean from two samples per arm and a 2.07× backend decode ratio. Those short runs do not measure task quality or end-to-end agent throughput.
- The practical workhorse cohort reports 8/12 valid artifacts passing on the first attempt, 10/12 after bounded feedback, and strict native acceptance on 2/13 tasks. It is not a cloud-equivalence study.
- The 99%+ lower-cloud-token target remains unmeasured. Hardware, electricity, model quality, retries, and advisor use affect any real cost comparison.
- GitHub snapshot on 2026-11-23: 0 stars, 0 forks, and no published release. These are public-repository visibility signals, not install or customer counts.

## Adoption friction and next experiment

High VRAM, Windows/NVIDIA, Docker GPU support, roughly 50 GB setup storage, model staging, and Sift compatibility limit the initial audience. The next decision-changing study is a small, preregistered developer pilot on at least two hardware profiles: record setup completion, repeated weekly use, task acceptance, local/cloud token receipts, latency, failures, and participant-reported trade-offs against each developer's normal hosted workflow. Do not claim market fit unless participants complete their own tasks and return for repeated use.

## Product and research values

- **Local ownership:** inference services bind to loopback by default; cloud advice is an explicit separate command.
- **Reproducibility:** pin runtime/model inputs where possible and publish raw receipts and the measurement boundary.
- **Separate outcomes:** decode speed, context retention, task acceptance, and cost answer different questions.
- **Honest uncertainty:** preserve failures and distinguish one-host evidence from portable product behavior.

## Sources

- [Project README and setup](../README.md)
- [Verification and limits](../VERIFICATION.md)
- [Practical workhorse results](../docs/WORKHORSE_USEFULNESS.md)
- [LM Studio local API server](https://lmstudio.ai/docs/developer/core/server)
- [LM Studio offline operation](https://lmstudio.ai/docs/app/offline)
