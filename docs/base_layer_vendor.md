# 基础层候选仓库接入记录

本文记录 `research_summary.md` 中基础层候选仓库的接入决策，避免后续把外部 SDK 和当前 Python 主控 Pipeline 混在一起。

## 已拉入仓库

```text
third_party/prometheus-avatar/
```

- 来源：https://github.com/myths-labs/prometheus-avatar
- 当前本地 HEAD：`2f46a7b7fbdd3f0f05603eacbfd9bc7a23177697`
- License：MIT，见 `third_party/prometheus-avatar/LICENSE`
- 技术栈：TypeScript / Node.js / pnpm
- 运行要求：Node >= 18，pnpm >= 8
- 核心 SDK：`third_party/prometheus-avatar/packages/sdk`
- 示例：`third_party/prometheus-avatar/examples`

## 为什么选择 Prometheus Avatar

`research_summary.md` 同时推荐了 `handcrafted-persona-engine` 和 `Prometheus Avatar SDK`。本次先拉入 Prometheus，原因是：

- 仓库中有明确 MIT License，课程项目复用风险较低。
- README 明确提供 SDK、Live2D、emotion、lip-sync、TTS 和 agent integration 入口。
- 它的 SDK 结构清晰，后续可以在 `AvatarController` 后面做一个 Web/SDK 适配层。
- 当前 Python 基础层已经实现 Mock Pipeline，不需要直接替换为完整第三方应用。

## 为什么没有直接拉入 handcrafted-persona-engine

调研文档中最推荐 `handcrafted-persona-engine`，但它更像完整 Windows/C# 桌面应用。按 PDF 要求，采用外部仓库前需要先验证 README、LICENSE、release、最小示例、平台要求和依赖范围。当前未把它拉入，主要因为：

- 公开页面未能在本地验证到可直接复用的 LICENSE 文件。
- 技术栈与当前 Python 主控层差异较大，整仓引入会提高维护成本。
- 它包含 ASR、RVC、桌面覆盖层等大量第一阶段不需要的功能。

后续如果一定要使用它，应先完成许可证和最小运行验证，再决定是参考架构、单独 fork，还是只抽取 emotion/action 设计。

## 和当前 Python 基础层的关系

当前项目仍以 Python 为主控层：

```text
User Text
  -> LLMProvider
  -> JSON Parser
  -> ActionPlanner
  -> TTSProvider
  -> AvatarController
```

Prometheus 目前只是候选真实 Avatar 层，不参与默认运行。默认仍使用：

- `MockLLMProvider`
- `MockTTSProvider`
- `MockAvatarController`

这样可以保证没有 API Key、没有 Live2D 模型、没有 Node 依赖时，完整 Pipeline 仍然可测试。

## 后续接入建议

1. Phase 3 先完成 Gradio UI，不依赖 Prometheus。
2. Phase 4/5 完成真实 LLM 和 Edge TTS。
3. Phase 6 再新增一个 `PrometheusAvatarController` 或 Web bridge。
4. Python 侧只发送标准化后的 `AvatarCommand`，不要让 TypeScript SDK 类型污染 Python 服务层。
5. 如果要运行 Prometheus 示例，在 `third_party/prometheus-avatar` 内单独执行 Node/pnpm 安装，不写入 Python 依赖。

## 保留模块

优先参考：

- `packages/sdk/src/avatar.ts`
- `packages/sdk/src/renderer.ts`
- `packages/sdk/src/emotion.ts`
- `packages/sdk/src/lip-sync.ts`
- `packages/sdk/src/tts.ts`
- `examples/basic`

暂不接入：

- Marketplace
- MCP server
- 多 LLM 示例
- 实时语音 / VAD / interrupt
- 摄像头 VTuber mode
