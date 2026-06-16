# Experiment Scripts

Thin wrappers around `deepresearch benchmark`. No business logic — all scripts
delegate to the CLI.

## Conventions

- Output: `outputs/experiments/<experiment_id>/`
- Each script accepts optional experiment ID as first argument
- Scripts exit non-zero on benchmark failure
- Real-mode scripts require `.env` with API keys

## Available Scripts

| Script | Purpose |
|--------|---------|
| `exp_local_mock` | Mock/local corpus smoke (CI, offline) |
| `exp_model_compare` | Compare LLM backends on same dataset |
| `exp_prompt_ablation` | Compare prompt labels |
| `exp_multilingual_large20` | Multilingual regression |
| `exp_full_suite` | Run all datasets, generate suite summary |
