"""Gradio UI for the chat avatar pipeline."""

import asyncio
import logging
import mimetypes
import os

import gradio as gr

from hai_avatar.app import build_pipeline
from hai_avatar.config import Settings, load_settings
from hai_avatar.exceptions import PipelineError
from hai_avatar.schemas import AvatarCommand

logger = logging.getLogger(__name__)


def _transcribe_audio(audio_path: str | None, settings: Settings) -> str:
    if not audio_path or not os.path.exists(audio_path):
        return ""
    try:
        from openai import OpenAI

        api_key = os.getenv(settings.llm.api_key_env, "")
        if not api_key:
            logger.warning("No API key for transcription; skipping ASR")
            return ""
        base_url = settings.llm.base_url
        model = os.getenv("ASR_MODEL", "whisper-1")
        mime_type = mimetypes.guess_type(audio_path)[0] or "application/octet-stream"
        client = OpenAI(api_key=api_key, base_url=base_url)
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=(os.path.basename(audio_path), f, mime_type),
            )
        logger.info("ASR transcribed: %s", transcript.text)
        return transcript.text
    except Exception as exc:
        logger.warning("ASR transcription failed: %s", exc)
        return ""


class GradioApp:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.service = build_pipeline(self.settings)
        self._loop = asyncio.new_event_loop()
        self._provider = self.settings.llm.provider
        self._tts_provider = self.settings.tts.provider

    async def _process_async(self, user_text: str, session_id: str = "default"):
        if not user_text or not user_text.strip():
            return "", "请输入内容", "", None
        try:
            result = await self.service.process(user_text, user_id=session_id)
        except PipelineError as exc:
            return "", "", str(exc), None
        except Exception as exc:
            logger.exception("Gradio request failed for session=%s", session_id)
            return "", "", f"请求处理失败，请稍后重试：{exc}", None
        status = self._format_status(result.avatar_command)
        warnings = "\n".join(result.warnings) if result.warnings else ""
        audio = result.audio_path if result.audio_path else None
        return result.reply_text, status, warnings, audio

    def process(self, user_text: str):
        return self._loop.run_until_complete(self._process_async(user_text, "local-cli"))

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
                    if self.settings.avatar.provider == "prometheus":
                        bridge_host = self.settings.avatar.bridge_host
                        browser_host = "127.0.0.1" if bridge_host == "0.0.0.0" else bridge_host
                        bridge_url = f"http://{browser_host}:{self.settings.avatar.bridge_port}/"
                        gr.HTML(
                            f'<iframe title="Live2D Avatar" src="{bridge_url}" '
                            'style="width:100%;height:420px;border:1px solid #333;border-radius:10px"></iframe>'
                        )
                    reply_text = gr.Textbox(label="AI 回复", lines=3, interactive=False)
                    audio_output = gr.Audio(label="语音播放", type="filepath")
                    avatar_status = gr.Textbox(label="Avatar 状态", lines=4, interactive=False)
                    warnings_output = gr.Textbox(label="系统提示", lines=2, interactive=False)

            async def respond(user_text: str, history: list, request: gr.Request):
                if not user_text or not user_text.strip():
                    return history, "", "", "", None
                session_id = request.session_hash or "local-session"
                reply, status, warnings, audio = await self._process_async(user_text, session_id)
                history = list(history or [])
                history.append({"role": "user", "content": user_text})
                if reply:
                    history.append({"role": "assistant", "content": reply})
                return history, reply, status, warnings, audio

            def transcribe_and_send(audio_path: str | None):
                if not audio_path:
                    return ""
                text = _transcribe_audio(audio_path, self.settings)
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

            async def clear_session(request: gr.Request):
                session_id = request.session_hash or "local-session"
                await self.service.clear_session(session_id)
                return [], "", "", "", None

            clear_btn.click(
                fn=clear_session,
                inputs=[],
                outputs=[chatbot, reply_text, avatar_status, warnings_output, audio_output],
            )

        return demo.queue(default_concurrency_limit=1, max_size=16)

    def run(self, port: int | None = None) -> None:
        if self.settings.avatar.provider == "prometheus":
            from hai_avatar.avatar.bridge_server import start_avatar_bridge_server
            from hai_avatar.config import PROJECT_ROOT

            output_dir = self.settings.avatar.prometheus_output_dir
            if not output_dir.is_absolute():
                output_dir = PROJECT_ROOT / output_dir
            start_avatar_bridge_server(
                output_dir,
                host=self.settings.avatar.bridge_host,
                port=self.settings.avatar.bridge_port,
            )
        demo = self.create_interface()
        demo.launch(
            server_name=self.settings.app.server_name,
            server_port=port or self.settings.app.server_port,
        )


def create_app(settings: Settings | None = None) -> gr.Blocks:
    return GradioApp(settings).create_interface()


if __name__ == "__main__":
    GradioApp().run()
