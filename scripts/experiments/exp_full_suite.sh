#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

EXPERIMENT_ID="${1:-full-suite-$(date +%Y%m%d-%H%M%S)}"

DATASETS=(
  "examples/bench/researchbench_smoke5.jsonl"
  "examples/bench/crosslingual_smoke10.jsonl"
  "examples/bench/multilingual_large20.jsonl"
  "examples/bench/hotpotqa_deepresearch.jsonl"
)

echo "=== Full Evaluation Suite ==="
echo "Experiment: ${EXPERIMENT_ID}"
echo ""

for ds in "${DATASETS[@]}"; do
  ds_name="$(basename "$ds" .jsonl)"
  EXP_ID="${EXPERIMENT_ID}-${ds_name}"
  OUTPUT="outputs/experiments/${EXP_ID}"

  echo "--- Running: ${ds_name} ---"
  uv run deepresearch benchmark "$ds" \
    --mode real \
    --retriever local \
    --corpus examples/corpus \
    --config examples/configs/benchmark_smoke.toml \
    --output "$OUTPUT" \
    --experiment "$EXP_ID" \
    || echo "WARNING: ${ds_name} failed, continuing..."
  echo ""
done

echo "=== Suite complete ==="
echo "Results in: outputs/experiments/${EXPERIMENT_ID}-*"
