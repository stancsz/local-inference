$ErrorActionPreference='Stop'
$modelDirectory=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../models')).Path
$runtime='ghcr.io/ggml-org/llama.cpp@sha256:b0baccbe2e00b5d74e63f85f9f023c93d61d0f329475269e1e7002e87eb875ea'
# Sequential copy into Docker's Linux filesystem avoids slow GGUF metadata
# and mmap access through a Windows bind mount. The named volume persists.
docker volume create local-inference-models | Out-Null
docker run --rm --entrypoint /bin/sh --mount "type=bind,source=$modelDirectory,target=/source,readonly" --mount 'type=volume,source=local-inference-models,target=/models' $runtime -c 'cp /source/Qwen3.8-27B-UD-IQ3_XXS.gguf /source/mtp-Qwen3.8-27B-Q4_0.gguf /models/'
if ($LASTEXITCODE -ne 0) { throw 'Model staging failed' }
