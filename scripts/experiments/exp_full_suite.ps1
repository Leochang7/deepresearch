#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir/../.."
Set-Location $ProjectRoot

$ExperimentId = if ($args.Count -gt 0) { $args[0] } else { "full-suite-$(Get-Date -Format 'yyyyMMdd-HHmmss')" }
$BaselineDir = if ($args.Count -gt 1) { $args[1] } else { "" }
$OutputRoot = "outputs/experiments/$ExperimentId"

$Datasets = @(
    "examples/bench/researchbench_smoke5.jsonl",
    "examples/bench/crosslingual_smoke10.jsonl",
    "examples/bench/multilingual_large20.jsonl",
    "examples/bench/hotpotqa_deepresearch.jsonl"
)
$Expected = @()

Write-Host "=== Full Evaluation Suite ==="
Write-Host "Experiment: $ExperimentId"
Write-Host ""

foreach ($ds in $Datasets) {
    $dsName = [System.IO.Path]::GetFileNameWithoutExtension($ds)
    $ExpId = "$dsName"
    $Expected += $ExpId

    Write-Host "--- Running: $dsName ---"
    try {
        uv run deepresearch benchmark $ds `
            --mode real `
            --retriever local `
            --corpus examples/corpus `
            --config examples/configs/benchmark_smoke.toml `
            --output $OutputRoot `
            --experiment $ExpId
    } catch {
        Write-Host "WARNING: $dsName failed, continuing..."
    }
    Write-Host ""
}

if ($BaselineDir) {
    uv run python -m deepresearch.evaluation.compare suite $OutputRoot --expected ($Expected -join ",") --before $BaselineDir
} else {
    uv run python -m deepresearch.evaluation.compare suite $OutputRoot --expected ($Expected -join ",")
}

Write-Host "=== Suite complete ==="
Write-Host "Results in: $OutputRoot"
Write-Host "Suite summary: $OutputRoot/suite_summary.json"
Write-Host "Comparison: $OutputRoot/comparison.json"
