# Experiment Scripts

Thin wrappers around `deepresearch benchmark`. No business logic — all scripts
delegate to the CLI.

## Conventions

- Output: `outputs/experiments/<experiment_id>/`; suite-style scripts use
  `outputs/experiments/<suite_id>/<dataset_or_variant>/`
- Each script accepts optional experiment ID as first argument
- Single-run smoke scripts exit non-zero on benchmark failure; comparison and
  suite scripts continue after individual failures and record missing/failed
  datasets in `suite_summary.json`
- Real-mode scripts require `.env` with API keys

## Available Scripts

| Script | Purpose |
|--------|---------|
| `exp_local_mock` | Mock/local corpus smoke (CI, offline) |
| `exp_model_compare` | Compare LLM backends on same dataset |
| `exp_prompt_ablation` | Compare prompt labels |
| `exp_multilingual_large20` | Multilingual regression |
| `exp_full_suite` | Run all datasets, generate suite summary |
