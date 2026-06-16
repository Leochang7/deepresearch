#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir/../.."
Set-Location $ProjectRoot

$Dataset = if ($args.Count -gt 0) { $args[0] } else { "examples/bench/researchbench_smoke5.jsonl" }
$ExperimentPrefix = if ($args.Count -gt 1) { $args[1] } else { "model-compare" }
$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'

$Models = @("mimo", "deepseek", "openai", "vllm")

foreach ($model in $Models) {
    $Config = "examples/configs/models/$model.toml"
    if (-not (Test-Path $Config)) {
        Write-Host "Skipping $model — config not found: $Config"
        continue
    }

    $ExpId = "$ExperimentPrefix-$model-$Timestamp"
    $Output = "outputs/experiments/$ExpId"

    Write-Host "=== Running: $model ==="
    try {
        uv run deepresearch benchmark $Dataset `
            --mode real `
            --retriever local `
            --corpus examples/corpus `
            --config $Config `
            --output $Output `
            --experiment $ExpId
    } catch {
        Write-Host "WARNING: $model failed, continuing..."
    }
    Write-Host ""
}

Write-Host "=== Model comparison complete ==="
