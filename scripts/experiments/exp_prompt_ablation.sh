#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

DATASET="${1:-examples/bench/researchbench_smoke5.jsonl}"
LABELS=("production" "staging")
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_ROOT="outputs/experiments/prompt-ablation-${TIMESTAMP}"
EXPECTED=()

for label in "${LABELS[@]}"; do
  EXP_ID="${label}"
  EXPECTED+=("$EXP_ID")

  echo "=== Prompt label: $label ==="
  uv run deepresearch benchmark "$DATASET" \
    --mode real \
    --retriever local \
    --corpus examples/corpus \
    --config examples/configs/benchmark_smoke.toml \
    --prompt-provider langfuse \
    --output "$OUTPUT_ROOT" \
    --experiment "$EXP_ID" \
    || echo "WARNING: $label failed, continuing..."
  echo ""
done

uv run python -m deepresearch.evaluation.compare suite "$OUTPUT_ROOT" \
  --expected "$(IFS=,; echo "${EXPECTED[*]}")"

echo "=== Prompt ablation complete ==="
echo "Results in: ${OUTPUT_ROOT}"
