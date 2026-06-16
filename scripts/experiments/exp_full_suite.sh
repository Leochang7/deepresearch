#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

EXPERIMENT_ID="${1:-full-suite-$(date +%Y%m%d-%H%M%S)}"
BASELINE_DIR="${2:-}"
OUTPUT_ROOT="outputs/experiments/${EXPERIMENT_ID}"

DATASETS=(
  "examples/bench/researchbench_smoke5.jsonl"
  "examples/bench/crosslingual_smoke10.jsonl"
  "examples/bench/multilingual_large20.jsonl"
  "examples/bench/hotpotqa_deepresearch.jsonl"
)
EXPECTED=()

echo "=== Full Evaluation Suite ==="
echo "Experiment: ${EXPERIMENT_ID}"
echo ""

for ds in "${DATASETS[@]}"; do
  ds_name="$(basename "$ds" .jsonl)"
  EXP_ID="${ds_name}"
  EXPECTED+=("$EXP_ID")

  echo "--- Running: ${ds_name} ---"
  uv run deepresearch benchmark "$ds" \
    --mode real \
    --retriever local \
    --corpus examples/corpus \
    --config examples/configs/benchmark_smoke.toml \
    --output "$OUTPUT_ROOT" \
    --experiment "$EXP_ID" \
    || echo "WARNING: ${ds_name} failed, continuing..."
  echo ""
done

COMPARE_ARGS=()
if [ -n "$BASELINE_DIR" ]; then
  COMPARE_ARGS=(--before "$BASELINE_DIR")
fi
uv run python -m deepresearch.evaluation.compare suite "$OUTPUT_ROOT" \
  --expected "$(IFS=,; echo "${EXPECTED[*]}")" \
  "${COMPARE_ARGS[@]}"

echo "=== Suite complete ==="
echo "Results in: ${OUTPUT_ROOT}"
echo "Suite summary: ${OUTPUT_ROOT}/suite_summary.json"
echo "Comparison: ${OUTPUT_ROOT}/comparison.json"
