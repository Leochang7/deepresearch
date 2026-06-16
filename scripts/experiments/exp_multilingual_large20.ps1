#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir/../.."
Set-Location $ProjectRoot

$ExperimentId = if ($args.Count -gt 0) { $args[0] } else { "multilingual-large20-$(Get-Date -Format 'yyyyMMdd-HHmmss')" }
$Output = "outputs/experiments/$ExperimentId"

Write-Host "=== Multilingual Large20 Regression ==="
Write-Host "Experiment: $ExperimentId"
Write-Host ""

uv run deepresearch benchmark `
  examples/bench/multilingual_large20.jsonl `
  --mode real `
  --retriever local `
  --corpus examples/corpus `
  --config examples/configs/benchmark_smoke.toml `
  --output $Output `
  --experiment $ExperimentId

Write-Host ""
Write-Host "Results: $Output/results.jsonl"
Write-Host "Summary: $Output/summary.json"
