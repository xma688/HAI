# Emotion- and Gesture-Aware AI Chat Avatar

这是 Human-AI Interaction 课程项目的基础 Pipeline。当前实现范围是 Phase 0-2：环境检查、项目骨架、完整 Mock Pipeline。真实 LLM、Edge TTS、Live2D/VTube Studio 和 Gradio 界面保留接口，后续阶段再接入。

## 架构

```text
User Text
  -> LLMProvider
  -> JSON Parser
  -> ActionPlanner
  -> TTSProvider
  -> AvatarController
  -> PipelineResult
```

核心模块都通过接口解耦：

- `LLMProvider`: 生成自然语言回复和控制标签
- `TTSProvider`: 生成音频文件
- `AvatarController`: 播放音频、切换表情、触发动作
- `ActionPlanner`: 校验、纠正、标准化标签
- `PipelineService`: 串联完整执行流程并记录耗时

## 目录结构

```text
config/                 YAML 配置和 LLM system prompt
assets/temp/            Mock TTS 运行时音频输出
src/hai_avatar/         主包
tests/                  单元测试和集成测试
scripts/run_mock.py     CLI Mock Demo
```

## 环境

- Python 3.11 或更高版本
- 当前基础 Mock 版本不依赖 GPU
- Mock TTS 生成 WAV，不要求 ffmpeg

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
python scripts/run_mock.py
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/run_mock.py
```

如果当前环境已经有依赖，也可以直接设置 `PYTHONPATH=src` 后运行脚本或测试。

## 配置

复制 `.env.example` 为 `.env` 后按需修改：

```text
LLM_PROVIDER=mock
TTS_PROVIDER=mock
AVATAR_PROVIDER=mock
LOG_LEVEL=INFO
```

默认 YAML 配置位于 `config/default.yaml`。不要把真实 API Key 写入代码或提交到仓库。

## Mock 模式

Mock 模式不需要 API Key、不需要 Live2D 模型，也不需要外部播放器。它会：

- 根据输入场景生成不同回复：greeting、supportive、explanation、confusion、farewell、apology、surprise、fallback
- 生成一个短 WAV 文件
- 在终端打印 Avatar 表情、动作、说话状态和音频路径

运行：

```powershell
$env:PYTHONPATH="src"
python scripts/run_mock.py "我最近项目压力有点大，不知道怎么开始。"
```

Windows PowerShell 管道可能会把中文传给外部程序时转码成问号；建议使用上面的命令行参数形式，或直接交互输入。

示例输入：

```text
我最近项目压力有点大，不知道怎么开始。
```

## 基础层候选仓库

根据 `research_summary.md` 的基础层路线，当前已把 MIT 许可的 Prometheus Avatar SDK 拉入：

```text
third_party/prometheus-avatar/
```

它是 TypeScript / Live2D SDK，可作为 Phase 6 真实 Avatar 层的候选实现参考。当前 Python Pipeline 不直接依赖它，仍然优先保证 Mock 模式稳定可运行。接入记录见 `docs/base_layer_vendor.md`。

## 测试

```powershell
$env:PYTHONPATH="src"
pytest
```

测试覆盖：

- 合法 JSON 解析
- Markdown JSON 修复
- 未知标签降级
- 动作数量截断
- 冲突标签纠正
- 动作冷却
- Mock TTS 文件生成
- Mock Avatar 执行
- Mock Pipeline 集成场景

## 当前限制

- OpenAIProvider 仅保留接口，占位到 Phase 4
- EdgeTTSProvider 仅保留接口，占位到 Phase 5
- Gradio UI 仅保留入口，占位到 Phase 3
- VTube Studio / Live2D 控制器仅保留接口，占位到 Phase 6
- Mock Avatar 只模拟播放和动作，不做真实口型同步

## 后续计划

1. Phase 3：实现 Gradio 文本输入、历史、标签显示、音频播放器和请求锁
2. Phase 4：接入真实 LLM，并实现结构化输出重试
3. Phase 5：接入 Edge TTS，明确语速/音高只是近似风格
4. Phase 6：验证并接入真实 Avatar 后端
5. Phase 7：补充超时、重试、清理策略和更完整 Demo
