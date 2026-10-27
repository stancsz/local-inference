#!/bin/sh
set -eu

set -- /app/llama-server --log-verbosity 4 \
  --model /models/Qwen3.8-27B-UD-IQ3_XXS.gguf \
  --alias qwen3.8-27b --host 0.0.0.0 --port 8080 \
  --ctx-size "${CONTEXT_SIZE:-40960}" --parallel 1 \
  --n-gpu-layers "${GPU_LAYERS:-99}" --fit off \
  --flash-attn on --cache-type-k q4_0 --cache-type-v q4_0 \
  --batch-size 256 --ubatch-size "${UBATCH_SIZE:-64}" \
  --no-context-shift --jinja --reasoning off --reasoning-budget 0 \
  --chat-template-kwargs '{"reasoning_effort":"low"}' \
  --no-reasoning-preserve --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0

case "${SPEC_TYPE:-draft-mtp}" in
  draft-mtp)
    set -- "$@" --spec-type draft-mtp \
      --gpu-layers-draft "${DRAFT_GPU_LAYERS:-99}" \
      --spec-draft-n-max "${DRAFT_TOKENS:-4}" \
      --cache-type-k-draft q4_0 --cache-type-v-draft q4_0
    ;;
  none) set -- "$@" --spec-type none ;;
  *) echo 'SPEC_TYPE must be draft-mtp or none' >&2; exit 2 ;;
esac
exec "$@"
