"""Gradio UI for the chat avatar pipeline."""

import asyncio
import logging
import os
from pathlib import Path

import gradio as gr

from hai_avatar.app import build_mock_pipeline
from hai_avatar.config import load_settings
from hai_avatar.schemas import AvatarCommand

logger = logging.getLogger(__name__)


def _transcribe_audio(audio_path: str | None) -> str:
    if not audio_path or not os.path.exists(audio_path):
        return ""
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENCODE_GO_API_KEY", "")
        if not api_key:
            logger.warning("No API key for transcription; skipping ASR")
            return ""
        base_url = os.getenv("LLM_BASE_URL", "https://opencode.ai/zen/go/v1")
        client = OpenAI(api_key=api_key, base_url=base_url)
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.wav", f, "audio/wav"),
            )
        logger.info("ASR transcribed: %s", transcript.text)
        return transcript.text
    except Exception as exc:
        logger.warning("ASR transcription failed: %s", exc)
        return ""


class GradioApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.service = build_mock_pipeline()
        self._loop = asyncio.new_event_loop()
        self._provider = self.settings.llm.provider
        self._tts_provider = self.settings.tts.provider

    async def _process_async(self, user_text: str):
        if not user_text or not user_text.strip():
            return "", "请输入内容", "", None
        result = await self.service.process(user_text)
        status = self._format_status(result.avatar_command)
        warnings = "\n".join(result.warnings) if result.warnings else ""
        audio = result.audio_path if result.audio_path else None
        return result.reply_text, status, warnings, audio

    def process(self, user_text: str):
        return self._loop.run_until_complete(self._process_async(user_text))

    def _format_status(self, cmd: AvatarCommand) -> str:
        gestures = ", ".join(g.value for g in cmd.gestures)
        return (
            f"情绪: {cmd.emotion.value} | "
            f"表情: {cmd.expression.value}\n"
            f"手势: {gestures} | "
            f"强度: {cmd.gesture_intensity:.2f}\n"
            f"语音风格: {cmd.voice_style.value} | "
            f"语速: {cmd.speaking_rate:.2f}"
        )

    def create_interface(self) -> gr.Blocks:
        provider_info = f"LLM: {self._provider} | TTS: {self._tts_provider}"

        with gr.Blocks(title="V Avatar") as demo:
            gr.Markdown("# V Avatar — 情绪与动作驱动的 AI 虚拟聊天代理")
            gr.Markdown(f"*{provider_info}*")

            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(height=400, label="对话")
                    with gr.Row():
                        user_input = gr.Textbox(
                            label="输入消息",
                            placeholder="输入你想说的话，或点击麦克风录音...",
                            lines=2,
                            scale=4,
                        )
                        send_btn = gr.Button("发送", variant="primary", scale=1)
                    with gr.Row():
                        mic_btn = gr.Audio(
                            sources=["microphone"],
                            type="filepath",
                            label="语音输入",
                        )
                    with gr.Row():
                        clear_btn = gr.Button("清空对话", size="sm")
                        gr.Examples(
                            examples=[
                                ["你好！很高兴认识你。"],
                                ["我最近项目压力很大，不知道该怎么办。"],
                                ["你能给我解释一下这个算法是怎么工作的吗？"],
                                ["谢谢你的帮助，再见！"],
                            ],
                            inputs=[user_input],
                            label="快捷示例",
                        )

                with gr.Column(scale=1):
                    reply_text = gr.Textbox(label="AI 回复", lines=3, interactive=False)
                    audio_output = gr.Audio(label="语音播放", type="filepath")
                    avatar_status = gr.Textbox(label="Avatar 状态", lines=4, interactive=False)
                    warnings_output = gr.Textbox(label="系统提示", lines=2, interactive=False)

            async def respond(user_text: str, history: list):
                if not user_text or not user_text.strip():
                    return history, "", "", "", None
                reply, status, warnings, audio = await self._process_async(user_text)
                history.append({"role": "user", "content": user_text})
                history.append({"role": "assistant", "content": reply})
                return history, reply, status, warnings, audio

            def transcribe_and_send(audio_path: str | None):
                if not audio_path:
                    return ""
                text = _transcribe_audio(audio_path)
                if not text:
                    return ""
                return text

            send_btn.click(
                fn=respond,
                inputs=[user_input, chatbot],
                outputs=[chatbot, reply_text, avatar_status, warnings_output, audio_output],
            ).then(fn=lambda: "", inputs=[], outputs=[user_input])

            user_input.submit(
                fn=respond,
                inputs=[user_input, chatbot],
                outputs=[chatbot, reply_text, avatar_status, warnings_output, audio_output],
            ).then(fn=lambda: "", inputs=[], outputs=[user_input])

            mic_btn.stop_recording(
                fn=transcribe_and_send,
                inputs=[mic_btn],
                outputs=[user_input],
            )

            clear_btn.click(
                fn=lambda: ([], "", "", "", None),
                inputs=[],
                outputs=[chatbot, reply_text, avatar_status, warnings_output, audio_output],
            )

        return demo

    def run(self, port: int = 7860) -> None:
        demo = self.create_interface()
        demo.launch(server_name="0.0.0.0", server_port=port)


def create_app() -> gr.Blocks:
    return GradioApp().create_interface()


if __name__ == "__main__":
    GradioApp().run()
