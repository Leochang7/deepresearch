#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

DATASET="${1:-examples/bench/researchbench_smoke5.jsonl}"
EXPERIMENT_PREFIX="${2:-model-compare}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_ROOT="outputs/experiments/${EXPERIMENT_PREFIX}-${TIMESTAMP}"

MODELS=("mimo" "deepseek" "openai" "vllm")
EXPECTED=()

for model in "${MODELS[@]}"; do
  CONFIG="examples/configs/models/${model}.toml"
  if [ ! -f "$CONFIG" ]; then
    echo "Skipping $model — config not found: $CONFIG"
    continue
  fi

  EXP_ID="${model}"
  EXPECTED+=("$EXP_ID")

  echo "=== Running: $model ==="
  uv run deepresearch benchmark "$DATASET" \
    --mode real \
    --retriever local \
    --corpus examples/corpus \
    --config "$CONFIG" \
    --output "$OUTPUT_ROOT" \
    --experiment "$EXP_ID" \
    || echo "WARNING: $model failed, continuing..."
  echo ""
done

uv run python -m deepresearch.evaluation.compare suite "$OUTPUT_ROOT" \
  --expected "$(IFS=,; echo "${EXPECTED[*]}")"

echo "=== Model comparison complete ==="
echo "Results in: ${OUTPUT_ROOT}"
