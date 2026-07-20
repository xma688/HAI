# HAI Evaluation MVP

This directory implements the runnable MVP from `docs/HAI_Evaluation_Implementation_Plan(1).pdf`.

Important naming boundary:

- `run_character_eval_subset.py` is a CharacterEval-derived local smoke test, not the official CharacterEval score.
- `run_official_character_eval.py` writes CharacterEval-compatible `generation.json` / `generation_trans.json`; `run_charactereval_charrm.py` then runs the official BaichuanCharRM reward model locally.
- `run_incharacter_bfi_self_report.py` uses InCharacter's official BFI questionnaire and scoring keys with a fixed HAI AvatarPersona. It is the self-report variant, not the full interview/evaluator-LLM pipeline.
- The main evaluation track is HAI-specific: profile correctness, counterfactual personalization, Action/Voice planning, and later real-user experiments.

## Commands

```powershell
python evaluation/runners/run_counterfactual.py --provider mock --condition full --limit 1
python evaluation/runners/run_action_eval.py --provider mock
python evaluation/runners/run_character_eval_subset.py --provider mock
```

## Official Benchmark Adapted Runs

The two PDFs name InCharacter and CharacterEval as benchmark references. This
repo now supports adapted local runs using their public GitHub data:

- CharacterEval: https://github.com/morecry/CharacterEval
- InCharacter: https://github.com/Neph0s/InCharacter

Fetch the official repos into `.tmp/` first:

```powershell
git clone --depth 1 https://github.com/morecry/CharacterEval.git .tmp\CharacterEval
git clone --depth 1 https://github.com/Neph0s/InCharacter.git .tmp\InCharacter
```

Prepare HAI-compatible subsets:

```powershell
python evaluation/adapters/prepare_official_benchmark_data.py --character-limit 20 --incharacter-limit 10
```

Run adapted benchmark experiments:

```powershell
python evaluation/runners/run_official_character_eval.py --provider mock --limit 2
python evaluation/runners/run_incharacter_bfi_adapted.py --provider mock --limit 2
```

Run the InCharacter BFI self-report scoring method:

```powershell
python evaluation/runners/run_incharacter_bfi_self_report.py --provider openai --allow-external-data-export
```

Build a visual report:

```powershell
python evaluation/reports/build_benchmark_report.py --runs <run_dir_1> <run_dir_2> --out evaluation/results/benchmark_report
```

Use `--provider openai --allow-external-data-export` for real API runs only
when external API export is allowed. Check `metrics.json` for
`llm_fallback_rate`; a non-zero value means the provider failed or the raw
response violated HAI's JSON schema and fallback responses affected the
pipeline.

For CharacterEval official reward-model scoring, first download
`morecry/BaichuanCharRM` locally, then run:

```powershell
python scripts/download_charrm.py
python evaluation/runners/run_charactereval_charrm.py --run-dir <charactereval_run_dir> --reward-model-path <local_BaichuanCharRM_dir>
```

Outputs are written to `evaluation/results/<run_id>/`:

- `manifest.json`
- `outputs.jsonl`
- `metrics.json`
- CharacterEval after CharacterRM: `charrm_evaluation.json`, `charrm_metrics.json`
- Report builder output: `benchmark_report.html`, `metrics_summary.csv`, and PNG charts

For formal runs, use `--provider openai`, freeze the commit/config/API model, and keep raw outputs plus planner/post-processor commands.

Do not report adapted runs as official overall scores unless the matching
official evaluator has been run. CharacterEval official scoring requires
CharacterRM. `run_incharacter_bfi_self_report.py` uses the official BFI
questionnaire scoring method, but it is still the self-report variant rather
than the full interview/evaluator-LLM pipeline.
