# HAI Evaluation MVP

This directory implements the runnable MVP from `HAI_Evaluation_Implementation_Plan(1).pdf`.

Important naming boundary:

- `run_character_eval_subset.py` is a CharacterEval-derived local smoke test, not the official CharacterEval score.
- InCharacter is not a formal score yet because the project has no independent `AvatarPersona`; current Big Five values are user profiles, not the avatar's own fixed personality.
- The main evaluation track is HAI-specific: profile correctness, counterfactual personalization, Action/Voice planning, and later real-user experiments.

## Commands

```powershell
python evaluation/runners/run_counterfactual.py --provider mock --condition full --limit 1
python evaluation/runners/run_action_eval.py --provider mock
python evaluation/runners/run_character_eval_subset.py --provider mock
```

Outputs are written to `evaluation/results/<run_id>/`:

- `manifest.json`
- `outputs.jsonl`
- `metrics.json`

For formal runs, use `--provider openai`, freeze the commit/config/API model, and keep raw outputs plus planner/post-processor commands.
