# HAI Chat Avatar

HAI Chat Avatar is a course project for an emotion- and gesture-aware virtual chat companion.

The current repository contains the integrated base layer, innovation layer, personalization layer, Live2D/Prometheus avatar bridge, real API support, and benchmark evaluation pipeline.

## What It Does

- Text chat pipeline: user input -> LLM response -> emotion/action planning -> TTS -> avatar command.
- Real LLM API: OpenAI-compatible `opencode/deepseek-v4-flash` through `.env`.
- Real TTS: Microsoft Edge TTS.
- Avatar bridge: Prometheus/Live2D browser bridge with model motion and basic expression/action command mapping.
- Personalization: user profile, Big Five style preference inference, prompt injection, and avatar command post-processing.
- Evaluation: CharacterEval adapted generation with local BaichuanCharRM scoring, plus InCharacter questionnaire self-report experiments across multiple HAI personas.

## Repository Structure

```text
config/                 Runtime config, action mapping, and LLM system prompt
docs/                   Course PDFs, benchmark notes, and research summary
src/hai_avatar/          Main Python package
  llm/                   Mock and OpenAI-compatible LLM providers
  tts/                   Mock and Edge TTS providers
  avatar/                Mock, VTube placeholder, and Prometheus controllers
  planner/               JSON validation, action planning, action mapping
  personalization/       Profile manager, prompt builder, post processor
  services/              Conversation and end-to-end pipeline services
  ui/                    Gradio UI
scripts/                 App launchers and utility scripts
evaluation/              Final benchmark evaluation pipeline
tests/                   Unit and integration tests
third_party/             Vendored Prometheus avatar bridge dependency
```

Large external benchmark repos and model weights are kept in `.tmp/` and are ignored by git:

```text
.tmp/CharacterEval/
.tmp/InCharacter/
.tmp/BaichuanCharRM/
```

## Setup

Use Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[all]"
```

Create `.env` from `.env.example`.

Mock mode needs no API key:

```text
LLM_PROVIDER=mock
TTS_PROVIDER=mock
AVATAR_PROVIDER=mock
PERSONALIZATION_ENABLED=true
```

Real API mode:

```text
LLM_PROVIDER=openai
LLM_MODEL=deepseek-v4-flash
TTS_PROVIDER=edge_tts
OPENCODE_GO_API_KEY=your_key_here
PERSONALIZATION_ENABLED=true
```

## Run

CLI smoke test:

```powershell
$env:PYTHONPATH="src"
python scripts\run_mock.py "我最近项目压力有点大"
```

Gradio UI:

```powershell
$env:PYTHONPATH="src"
python scripts\run_gradio.py
```

Real API + Prometheus avatar bridge:

```powershell
$env:PYTHONPATH="src"
python scripts\run_real_api_prometheus.py "你好，请用中文回复我。"
```

The generated audio is written under `assets/audio/`; temporary browser/avatar bridge files are written under `assets/temp/`.

## Evaluation

The final evaluation code is in `evaluation/`.

Final retained result directories:

```text
evaluation/results/charactereval_official_adapted_20260720T090123Z/
evaluation/results/incharacter_bfi_personas_20260723T065833Z/
evaluation/results/incharacter_bfi_personas_repeat2_20260724/
evaluation/results/incharacter_empathy_personas_20260724/
evaluation/results/incharacter_bfi_control_20260724/
evaluation/results/benchmark_report_20260723T0710_incharacter_expanded/
evaluation/results/incharacter_small_experiments_20260724/
```

Open these reports directly in a browser:

```text
evaluation/results/benchmark_report_20260723T0710_incharacter_expanded/benchmark_report.html
evaluation/results/incharacter_small_experiments_20260724/incharacter_small_experiments.html
```

Rebuild official adapted data:

```powershell
$env:PYTHONPATH="src"
python evaluation\adapters\prepare_official_benchmark_data.py --character-limit 60 --character-selection balanced --incharacter-limit 44
```

Run CharacterEval adapted generation with real API:

```powershell
$env:PYTHONPATH="src"
python evaluation\runners\run_official_character_eval.py --provider openai --allow-external-data-export --output evaluation\results\charactereval_new
```

Run local BaichuanCharRM scoring:

```powershell
$env:PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
$env:PYTHONPATH="src"
python evaluation\runners\run_charactereval_charrm.py --run-dir evaluation\results\charactereval_new --reward-model-path .tmp\BaichuanCharRM --max-records-per-metric 3
```

Run InCharacter BFI/Empathy questionnaire experiments:

```powershell
$env:PYTHONPATH="src"
python evaluation\runners\run_incharacter_questionnaire_personas.py --questionnaire .tmp\InCharacter\data\questionnaires\BFI.json --provider openai --allow-external-data-export
python evaluation\runners\run_incharacter_questionnaire_personas.py --questionnaire .tmp\InCharacter\data\questionnaires\Empathy.json --provider openai --allow-external-data-export
```

## Tests

```powershell
$env:PYTHONPATH="src"
pytest
```

Expected current status: 36 tests passing.

## Current Evaluation Boundary

CharacterEval uses official public data and local BaichuanCharRM scoring, but the retained run is a balanced adapted subset rather than a full official leaderboard submission.

InCharacter uses official questionnaire items and scoring logic in a self-report protocol across fixed HAI persona presets. It is suitable for course analysis of personality controllability, but it is not the full original interview plus evaluator-LLM protocol.
