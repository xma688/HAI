# Changelog

## 0.2.0 - 2026-07-22

### Fixed

- 按 Gradio Session ID 隔离对话历史和动作冷却，并让清空按钮同步清理后端状态。
- 串行化 Avatar 播放，避免并发请求造成表情、动作和音频交错。
- 为不完整或越界的 LLM 控制字段提供默认值与范围校验，避免回显无效 JSON。
- 将语速传给 TTS，将动作强度传给 Avatar；限制过长的说话前停顿。
- 修正 Edge TTS 音频格式：通过 ffmpeg 将 MP3 转为真正的 WAV，并加入超时处理。
- 停用根据系统自己选出的动作自动强化用户偏好的错误反馈回路。
- 对用户画像文件名进行安全处理，防止 Session ID 越界写入画像目录。
- 修复本地评测脚本对会话化历史接口的调用。
- 清空 Gradio 会话时同步移除 Live2D bridge 中的上一轮文本、音频和事件。

### Changed

- Prometheus bridge 使用轮次状态、原子状态文件、可访问音频 URL 和 250 ms 轮询。
- Live2D 浏览器端播放生成音频、同步口型，并按动作强度调整参数幅度。
- Gradio 在 Prometheus 模式下自动启动并嵌入本地 bridge，默认仅监听 `127.0.0.1`。
- `scripts/run_gradio.py` 完全尊重 `.env` 中的 provider 与网络配置，不再强制覆盖。
- 真实 API Prometheus 冒烟脚本不再强制使用本地 MOSS TTS，并尊重 `.env` 的 key 变量与 TTS 配置。
- OpenAI SDK 内部重试关闭，由管线统一执行重试策略。

### Tests

- 新增会话隔离、清空、动作冷却、显式偏好反馈、字段兼容、参数校验和 Prometheus 状态回归测试。
