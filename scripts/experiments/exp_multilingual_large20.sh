#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

EXPERIMENT_ID="${1:-multilingual-large20-$(date +%Y%m%d-%H%M%S)}"
OUTPUT="outputs/experiments/${EXPERIMENT_ID}"

echo "=== Multilingual Large20 Regression ==="
echo "Experiment: ${EXPERIMENT_ID}"
echo ""

uv run deepresearch benchmark \
  examples/bench/multilingual_large20.jsonl \
  --mode real \
  --retriever local \
  --corpus examples/corpus \
  --config examples/configs/benchmark_smoke.toml \
  --output "$OUTPUT" \
  --experiment "$EXPERIMENT_ID"

echo ""
echo "Results: ${OUTPUT}/results.jsonl"
echo "Summary: ${OUTPUT}/summary.json"
