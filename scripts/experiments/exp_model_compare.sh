#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

DATASET="${1:-examples/bench/researchbench_smoke5.jsonl}"
EXPERIMENT_PREFIX="${2:-model-compare}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

MODELS=("mimo" "deepseek" "openai" "vllm")

for model in "${MODELS[@]}"; do
  CONFIG="examples/configs/models/${model}.toml"
  if [ ! -f "$CONFIG" ]; then
    echo "Skipping $model — config not found: $CONFIG"
    continue
  fi

  EXP_ID="${EXPERIMENT_PREFIX}-${model}-${TIMESTAMP}"
  OUTPUT="outputs/experiments/${EXP_ID}"

  echo "=== Running: $model ==="
  uv run deepresearch benchmark "$DATASET" \
    --mode real \
    --retriever local \
    --corpus examples/corpus \
    --config "$CONFIG" \
    --output "$OUTPUT" \
    --experiment "$EXP_ID" \
    || echo "WARNING: $model failed, continuing..."
  echo ""
done

echo "=== Model comparison complete ==="
echo "Results in: outputs/experiments/${EXPERIMENT_PREFIX}-*"
