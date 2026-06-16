#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir/../.."
Set-Location $ProjectRoot

$ExperimentId = if ($args.Count -gt 0) { $args[0] } else { "full-suite-$(Get-Date -Format 'yyyyMMdd-HHmmss')" }

$Datasets = @(
    "examples/bench/researchbench_smoke5.jsonl",
    "examples/bench/crosslingual_smoke10.jsonl",
    "examples/bench/multilingual_large20.jsonl",
    "examples/bench/hotpotqa_deepresearch.jsonl"
)

Write-Host "=== Full Evaluation Suite ==="
Write-Host "Experiment: $ExperimentId"
Write-Host ""

foreach ($ds in $Datasets) {
    $dsName = [System.IO.Path]::GetFileNameWithoutExtension($ds)
    $ExpId = "$ExperimentId-$dsName"
    $Output = "outputs/experiments/$ExpId"

    Write-Host "--- Running: $dsName ---"
    try {
        uv run deepresearch benchmark $ds `
            --mode real `
            --retriever local `
            --corpus examples/corpus `
            --config examples/configs/benchmark_smoke.toml `
            --output $Output `
            --experiment $ExpId
    } catch {
        Write-Host "WARNING: $dsName failed, continuing..."
    }
    Write-Host ""
}

Write-Host "=== Suite complete ==="
