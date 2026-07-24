# HAI Evaluation

This directory contains the cleaned final evaluation pipeline for the HAI chat-avatar system.

The earlier MVP/mock evaluation scripts and toy datasets have been removed. The retained path focuses on the two selected benchmark families:

- CharacterEval: official public samples adapted to the HAI pipeline, then scored with local `morecry/BaichuanCharRM`.
- InCharacter: official questionnaire files, scored as self-report experiments across fixed HAI avatar personas.

## Directory Layout

```text
adapters/
  prepare_official_benchmark_data.py     Build official adapted CharacterEval/InCharacter data artifacts
datasets/official_adapted/
  charactereval_official_subset.jsonl    Balanced CharacterEval adapted subset
  incharacter_bfi_official_subset.jsonl  Prepared BFI artifact kept for provenance
  source_metadata.json                   Official source repo metadata and coverage
runners/
  run_official_character_eval.py         Generate HAI responses for CharacterEval adapted data
  run_charactereval_charrm.py            Score generated responses with local BaichuanCharRM
  run_incharacter_questionnaire_personas.py
                                          Run BFI/Empathy questionnaires across HAI personas
scorers/
  dialogue_metrics.py                    Local proxy metrics for generated dialogue quality
  incharacter_questionnaire_scoring.py   Questionnaire scoring and target comparison
reports/
  build_benchmark_report.py              Combined benchmark HTML/CSV/PNG report
  summarize_incharacter_small_experiments.py
                                          BFI repeat, Empathy, and ablation summary report
results/
  ...                                    Only final retained result directories
```

## External Data Boundary

Real API evaluation sends benchmark prompts and persona descriptions to an external provider. Runners refuse this unless `--allow-external-data-export` is passed explicitly.

## Reproduce Final-Style Runs

Prepare official adapted data:

```powershell
$env:PYTHONPATH="src"
python evaluation\adapters\prepare_official_benchmark_data.py --character-limit 60 --character-selection balanced --incharacter-limit 44
```

Run CharacterEval adapted generation:

```powershell
$env:PYTHONPATH="src"
python evaluation\runners\run_official_character_eval.py --provider openai --allow-external-data-export --output evaluation\results\charactereval_new
```

Run CharacterRM sampled scoring:

```powershell
$env:PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
$env:PYTHONPATH="src"
python evaluation\runners\run_charactereval_charrm.py --run-dir evaluation\results\charactereval_new --reward-model-path .tmp\BaichuanCharRM --max-records-per-metric 3
```

Run InCharacter BFI:

```powershell
$env:PYTHONPATH="src"
python evaluation\runners\run_incharacter_questionnaire_personas.py --questionnaire .tmp\InCharacter\data\questionnaires\BFI.json --provider openai --allow-external-data-export
```

Run InCharacter Empathy:

```powershell
$env:PYTHONPATH="src"
python evaluation\runners\run_incharacter_questionnaire_personas.py --questionnaire .tmp\InCharacter\data\questionnaires\Empathy.json --provider openai --allow-external-data-export
```

Build the combined benchmark report:

```powershell
$env:PYTHONPATH="src"
python evaluation\reports\build_benchmark_report.py --runs evaluation\results\charactereval_official_adapted_20260720T090123Z evaluation\results\incharacter_bfi_personas_20260723T065833Z --out evaluation\results\benchmark_report_new
```

Build the InCharacter small-experiment report:

```powershell
$env:PYTHONPATH="src"
python evaluation\reports\summarize_incharacter_small_experiments.py --bfi-runs evaluation\results\incharacter_bfi_personas_20260723T065833Z evaluation\results\incharacter_bfi_personas_repeat2_20260724 --empathy-run evaluation\results\incharacter_empathy_personas_20260724 --control-run evaluation\results\incharacter_bfi_control_20260724 --out evaluation\results\incharacter_small_experiments_new
```

## Retained Final Results

```text
evaluation/results/charactereval_official_adapted_20260720T090123Z/
evaluation/results/incharacter_bfi_personas_20260723T065833Z/
evaluation/results/incharacter_bfi_personas_repeat2_20260724/
evaluation/results/incharacter_empathy_personas_20260724/
evaluation/results/incharacter_bfi_control_20260724/
evaluation/results/benchmark_report_20260723T0710_incharacter_expanded/
evaluation/results/incharacter_small_experiments_20260724/
```

Main reports:

```text
evaluation/results/benchmark_report_20260723T0710_incharacter_expanded/benchmark_report.html
evaluation/results/incharacter_small_experiments_20260724/incharacter_small_experiments.html
```

## Reporting Boundary

Do not present these as full official leaderboard scores.

CharacterEval is an official-data adapted subset with local CharacterRM scoring. InCharacter uses official questionnaire items and scoring rules in a HAI self-report setup, not the full original interview/evaluator protocol.
