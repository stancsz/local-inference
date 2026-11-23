# Local Large Language Model Inference with Speculative Decoding on a 16 GB GPU

Matched decode measurements and a supervised coding-workflow evaluation

## Abstract

This report documents local inference using a quantized Qwen3.8-27B model with shared-weight multi-token prediction [R1] on one Windows workstation with an NVIDIA RTX 5070 Ti 16 GB GPU. In a matched two-sample comparison, MTP decode rates of 101.58 and 103.92 tokens/s averaged 102.75 tokens/s; corresponding no-MTP samples averaged 49.65 tokens/s. The ratio of these sample means is 2.07. A separate practical task pack recorded 8 of 12 valid artifacts passing first attempt and 10 of 12 after bounded feedback; strict native workflow acceptance was 2 of 13 tasks. These are host-specific observations under different protocols. They do not establish general task quality, cloud parity, unattended reliability, or a 99% cloud-cost reduction.

## 1. System scope

The repository documents a LiteLLM gateway backed by a Dockerized quantized Qwen3.8-27B model and llama.cpp [R2] on one Windows machine with an RTX 5070 Ti 16 GB GPU. The gateway binds to loopback. An optional cloud advisor is invoked separately and is not an automatic fallback.

Sift runs as a CPU callback in the gateway. This is a concrete host configuration, not a general deployment result for arbitrary hardware.

## 2. Matched decode measurements

The repository records [R3] the shared-weight MTP comparison two enabled samples at 101.58 and 103.92 tokens/s, mean 102.75. The matched no-MTP samples average 49.65 tokens/s; the ratio of these means is 2.07. Enabled runs used four draft tokens, a configured 40,960-token context window, and a 256-token output. Configured window capacity is not fully populated context length.

A previous separate-draft configuration measured 103.45 tokens/s, and a separate full synthetic-context profile measured 60.88 tokens/s. These are distinct experiments and should not be merged into the matched pair.

## Product and research values

The product goal is supervised local development work: run token-heavy inference and tool loops on one workstation, keep the gateway local, and make optional cloud-advisor use explicit.

- **Reproducible speed claim:** 102.75 tok/s is the mean of two matched MTP samples on the documented host.
- **Separate evidence classes:** throughput, synthetic capacity, context retention, and practical task acceptance answer different questions.
- **Bounded task evidence:** 8/12 valid artifacts passed first attempt and 10/12 after bounded feedback; strict native acceptance was 2/13.
- **No unsupported savings or parity:** 99% lower cloud-token usage remains a target; general reliability and cloud equivalence are not established.

## 3. Limitations and future work

The thirteen-task usefulness pack included one invalid CSV case. Of twelve valid artifacts, eight passed first attempt and ten passed after bounded feedback. Strict native workflow acceptance was two of thirteen. These use different acceptance conditions and should not be pooled.

Evidence comes from one host and small samples. Decode speed does not measure code correctness or total user time. Future comparisons should preregister tasks, match prompts and tool access, report all attempts, use independent artifact review, and account for advisor calls, retries, hardware electricity, and equivalent cloud-only work. A 99% savings claim remains a target to measure.

## 4. Conclusion

The recorded MTP setup increased measured decode throughput in a small matched comparison, while practical tasks retained meaningful quality limitations. Evidence supports a bounded local-workflow investigation, not broad claims of cloud replacement.

## References

[R1] Cai, T., et al. Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads. 2024. URL: https://arxiv.org/abs/2401.10774
[R2] Gerganov, G. llama.cpp: LLM inference in C/C++. URL: https://github.com/ggml-org/llama.cpp
[R3] Chen, S. Local Inference repository and verification records. URL: https://github.com/stancsz/local-inference