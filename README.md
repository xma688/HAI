# Emotion- and Gesture-Aware AI Chat Avatar

情绪与动作驱动的 AI 虚拟聊天代理 — Human-AI Interaction 课程项目。

## 项目概述

用户输入文本 → LLM 生成回复 + 情绪/动作推理 → TTS 合成语音 → 虚拟角色播放语音并做表情动作。核心创新是一个**语义到动作的映射模块**（Action Planner），让 LLM 不仅回答问题，还能判断当前的情绪、语气、表情和动作。

当前已实现完整的 **Mock 管线 + 真实 LLM (opencode/deepseek-v4-flash) + 真实 TTS (Edge TTS) + 个性化层 + 创新层 + Gradio Web UI + 用户实验工具**。唯一未接入的是真实 Live2D Avatar 渲染。

## 三层架构

```
┌──────────────────────────────────────────────────────────┐
│ 基础层: LLM / TTS / Avatar / Gradio UI                  │
│ Mock 模式开箱即用，真实 LLM/TTS 通过配置切换              │
├──────────────────────────────────────────────────────────┤
│ 创新层: Action Reasoning                                 │
│ 7 步推理框架 (情绪→表情→动作→强度→语音→语速→停顿)         │
│ 对话历史上下文注入，few-shot 示例引导                     │
├──────────────────────────────────────────────────────────┤
│ 个性化层: Agent Personalization                          │
│ UserProfile (Big Five 人格推断 + 偏好学习)                │
│ Prompt 注入 (画像→自然语言指令) + PostProcessor (参数约束)  │
└──────────────────────────────────────────────────────────┘
```

## Pipeline

```text
User Text + 对话历史
  -> [个性化层] ProfileManager 加载/构建用户画像
  -> [个性化层] PromptBuilder 注入个性化系统指令
  -> [基础层]   LLMProvider (Mock / OpenAI)
  -> [基础层]   JSON Parser + Fallback
  -> [创新层]   ActionPlanner (透传 intensity/rate)
  -> [个性化层] PostProcessor (画像约束→参数调整)
  -> [基础层]   TTSProvider (Mock / Edge TTS)
  -> [基础层]   AvatarController (Mock)
  -> PipelineResult
```

## 目录结构

```text
config/                    YAML 配置和 LLM system prompt
  llm_system_prompt.txt    7 步动作推理框架 + few-shot 示例
  action_mapping.yaml      动作冷却和默认映射
  default.yaml             总配置
scripts/
  run_mock.py              CLI Demo（快速测试）
  run_gradio.py            Gradio Web UI 启动器
  run_experiment.py        用户实验 A/B/C 对比工具
src/hai_avatar/
  llm/                     LLM 提供商
    mock_provider.py       8 场景规则生成器
    openai_provider.py     真实 API (opencode / deepseek-v4-flash)
  tts/                     TTS 提供商
    mock_provider.py       生成频率调制的 WAV
    edge_tts_provider.py   Microsoft Edge 免费中文 TTS
  avatar/                  虚拟角色控制
    mock_controller.py     终端日志模拟
    vtube_studio_controller.py  占位 (Phase 6 Live2D)
  planner/                 动作规划与校验
    action_planner.py      规则校验 + 一致性检查 + 冷却
    validator.py           JSON 解析 + Fallback
    mapping.py             YAML 配置加载
  personalization/         个性化层
    profile_manager.py     JSON 持久化 + Big Five 关键词推断
    prompt_builder.py      画像 → 自然语言指令
    post_processor.py      画像 → AvatarCommand 参数约束
  services/
    pipeline_service.py    总管线 (含重试/降级)
    conversation_service.py  对话历史存储
  ui/
    gradio_app.py          Web UI (聊天 + 语音 + 状态显示)
  schemas.py               所有 Pydantic 数据模型
  config.py                配置加载 (YAML + 环境变量)
data/                      运行时数据
  profiles/                用户画像 JSON
  experiment_results.csv   用户实验记录
tests/                     33 个单元/集成测试
```

## 快速开始

### 1. 环境

```bash
# Python 3.11+
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env 选择运行模式
```

```text
# .env  — Mock 模式 (无需任何 API Key)
LLM_PROVIDER=mock
TTS_PROVIDER=mock
PERSONALIZATION_ENABLED=true
```

```text
# .env  — 真实模式 (需要 opencode API Key)
LLM_PROVIDER=openai
LLM_MODEL=deepseek-v4-flash
TTS_PROVIDER=edge_tts
OPENCODE_GO_API_KEY=your_key_here
PERSONALIZATION_ENABLED=true
```

### 3. 运行

```bash
# CLI 测试（Mock 模式）
PYTHONPATH=src python scripts/run_mock.py "我最近项目压力有点大"

# CLI 测试（真实 LLM）
LLM_PROVIDER=openai PYTHONPATH=src python scripts/run_mock.py "你好"

# 启动 Web UI
PYTHONPATH=src python scripts/run_gradio.py

# 真实 LLM + 真实语音
LLM_PROVIDER=openai TTS_PROVIDER=edge_tts PYTHONPATH=src python scripts/run_gradio.py
```

### 4. 用户实验

```bash
# 随机分配实验模式
PYTHONPATH=src python scripts/run_experiment.py

# 强制指定模式 (A=纯文本 B=语音 C=完整)
PYTHONPATH=src python scripts/run_experiment.py --mode C

# 查看统计数据
PYTHONPATH=src python scripts/run_experiment.py --stats
```

## 测试

```bash
PYTHONPATH=src pytest    # 33 个测试全部通过
```

覆盖：JSON 解析/修复、标签降级、截断、冲突纠正、冷却、Mock TTS/Avatar/Pipeline、用户画像构建/加载/更新、Big Five 推断、Prompt 生成、PostProcessor 约束、对话历史累积、完全管线（启用/禁用个性化）。

## 枚举标签

| 类别 | 可选值 |
|------|--------|
| emotion | neutral, happy, supportive, thoughtful, confused, surprised, serious, apologetic |
| expression | neutral, smile, soft_smile, thinking, confused, surprised, concerned, serious |
| gestures | idle, nod, wave, head_tilt, think, explain, agree, small_bow |
| voice_style | neutral, calm, cheerful, gentle, serious, apologetic |

## 配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LLM_PROVIDER` | mock | mock / openai |
| `LLM_MODEL` | deepseek-v4-flash | LLM 模型名 |
| `TTS_PROVIDER` | mock | mock / edge_tts |
| `AVATAR_PROVIDER` | mock | mock |
| `OPENCODE_GO_API_KEY` | — | opencode API Key |
| `PERSONALIZATION_ENABLED` | true | 启用个性画像 |

## 当前限制

- VTube Studio / Live2D Avatar 仅有接口占位，未实现真实渲染
- ASR 语音输入仅在有 API Key 时可用（通过 Gradio 麦克风触发）
- Mock Avatar 仅打日志，不做真实口型同步
