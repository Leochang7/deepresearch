#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir/../.."
Set-Location $ProjectRoot

$Dataset = if ($args.Count -gt 0) { $args[0] } else { "examples/bench/researchbench_smoke5.jsonl" }
$Labels = @("production", "staging")
$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'

foreach ($label in $Labels) {
    $ExpId = "prompt-ablation-$label-$Timestamp"
    $Output = "outputs/experiments/$ExpId"

    Write-Host "=== Prompt label: $label ==="
    try {
        uv run deepresearch benchmark $Dataset `
            --mode real `
            --retriever local `
            --corpus examples/corpus `
            --config examples/configs/benchmark_smoke.toml `
            --prompt-provider langfuse `
            --output $Output `
            --experiment $ExpId
    } catch {
        Write-Host "WARNING: $label failed, continuing..."
    }
    Write-Host ""
}

Write-Host "=== Prompt ablation complete ==="
