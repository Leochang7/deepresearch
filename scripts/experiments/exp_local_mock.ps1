#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir/../.."
Set-Location $ProjectRoot

$ExperimentId = if ($args.Count -gt 0) { $args[0] } else { "local-mock-$(Get-Date -Format 'yyyyMMdd-HHmmss')" }
$Output = "outputs/experiments/$ExperimentId"

Write-Host "=== Local Mock Smoke ==="
Write-Host "Experiment: $ExperimentId"
Write-Host ""

uv run deepresearch benchmark `
  examples/bench/researchbench_smoke5.jsonl `
  --mode mock `
  --retriever local `
  --corpus examples/corpus `
  --output $Output `
  --experiment $ExperimentId

Write-Host ""
Write-Host "Results: $Output/results.jsonl"
Write-Host "Summary: $Output/summary.json"
