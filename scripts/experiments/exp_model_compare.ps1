#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir/../.."
Set-Location $ProjectRoot

$Dataset = if ($args.Count -gt 0) { $args[0] } else { "examples/bench/researchbench_smoke5.jsonl" }
$ExperimentPrefix = if ($args.Count -gt 1) { $args[1] } else { "model-compare" }
$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$OutputRoot = "outputs/experiments/$ExperimentPrefix-$Timestamp"

$Models = @("mimo", "deepseek", "openai", "vllm")
$Expected = @()

foreach ($model in $Models) {
    $Config = "examples/configs/models/$model.toml"
    if (-not (Test-Path $Config)) {
        Write-Host "Skipping $model — config not found: $Config"
        continue
    }

    $ExpId = "$model"
    $Expected += $ExpId

    Write-Host "=== Running: $model ==="
    try {
        uv run deepresearch benchmark $Dataset `
            --mode real `
            --retriever local `
            --corpus examples/corpus `
            --config $Config `
            --output $OutputRoot `
            --experiment $ExpId
    } catch {
        Write-Host "WARNING: $model failed, continuing..."
    }
    Write-Host ""
}

uv run python -m deepresearch.evaluation.compare suite $OutputRoot --expected ($Expected -join ",")

Write-Host "=== Model comparison complete ==="
Write-Host "Results in: $OutputRoot"
