"""Gradio UI for the chat avatar pipeline."""

import asyncio
import html
import logging
import mimetypes
import os
from pathlib import Path

import gradio as gr

from hai_avatar.app import build_pipeline
from hai_avatar.config import PROJECT_ROOT, Settings, load_settings
from hai_avatar.exceptions import PipelineError
from hai_avatar.schemas import AvatarCommand

logger = logging.getLogger(__name__)

BRAND_ASSET_DIR = PROJECT_ROOT / "assets" / "brand"
ICON_PATH = BRAND_ASSET_DIR / "hai-companion-icon.png"
HERO_PATH = BRAND_ASSET_DIR / "hero-companion.jpg"
STORY_IMAGES = (
    (BRAND_ASSET_DIR / "emotion-understanding.jpg", "理解情绪，而不只识别关键词"),
    (BRAND_ASSET_DIR / "natural-voice.jpg", "让语气、语速与内容保持一致"),
    (BRAND_ASSET_DIR / "expressive-avatar.jpg", "表情与动作跟随每轮对话"),
    (BRAND_ASSET_DIR / "quiet-companionship.jpg", "在需要的时候，安静地陪着你"),
)
STYLES_PATH = Path(__file__).with_name("styles.css")


def _file_url(path: Path) -> str:
    return f"/gradio_api/file={html.escape(path.resolve().as_posix(), quote=True)}"


def _provider_label(value: str) -> str:
    return value.replace("_", " ").upper()


def _brand_header(icon_path: Path, provider: str, tts_provider: str, avatar_provider: str) -> str:
    if icon_path.exists():
        mark = f'<img src="{_file_url(icon_path)}" alt="HAI Companion icon">'
    else:
        mark = '<span class="hai-brand-fallback">HAI</span>'
    return f"""
    <nav class="hai-nav" aria-label="产品信息">
      <div class="hai-brand">{mark}<span>HAI · Empathetic Companion</span></div>
      <div class="hai-nav-meta">
        <span class="hai-chip live">系统就绪</span>
        <span class="hai-chip">LLM {_provider_label(provider)}</span>
        <span class="hai-chip">TTS {_provider_label(tts_provider)}</span>
        <span class="hai-chip">AVATAR {_provider_label(avatar_provider)}</span>
      </div>
    </nav>
    """


def _hero_copy() -> str:
    return """
    <section class="hai-hero">
      <span class="hai-kicker">Emotion · Voice · Expression</span>
      <h1>不只是回答，<br><span>也在认真回应。</span></h1>
      <p>HAI 将自然对话、情绪理解、语音合成与 Live2D 表现连接在同一条实时链路里，让每一句回复都有合适的语气、表情与动作。</p>
      <div class="hai-hero-pills">
        <span class="hai-pill">上下文对话</span>
        <span class="hai-pill">自然中文语音</span>
        <span class="hai-pill">情绪与动作联动</span>
      </div>
    </section>
    """


def _section_heading(kicker: str, title: str, description: str) -> str:
    return f"""
    <div class="hai-section-heading">
      <div><span class="hai-kicker">{html.escape(kicker)}</span><h2>{html.escape(title)}</h2></div>
      <p>{html.escape(description)}</p>
    </div>
    """


def _initial_status() -> str:
    return """
    <div class="hai-status-grid">
      <div class="hai-status-item"><small>Emotion</small><strong>等待对话</strong></div>
      <div class="hai-status-item"><small>Expression</small><strong>neutral</strong></div>
      <div class="hai-status-item"><small>Gesture</small><strong>idle</strong></div>
      <div class="hai-status-item"><small>Voice</small><strong>neutral</strong></div>
      <div class="hai-status-item"><small>Intensity</small><strong>0.50</strong></div>
      <div class="hai-status-item"><small>Latency</small><strong>—</strong></div>
    </div>
    """


def _notice(message: str, *, error: bool = False) -> str:
    kind = " error" if error else ""
    return f'<div class="hai-notice{kind}">{html.escape(message)}</div>'


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
            return "", _notice("请输入内容后再发送。"), "", None
        try:
            result = await self.service.process(user_text, user_id=session_id)
        except PipelineError as exc:
            return "", _notice(str(exc), error=True), "", None
        except Exception as exc:
            logger.exception("Gradio request failed for session=%s", session_id)
            return "", _notice("请求处理失败，请稍后重试。", error=True), "", None
        status = self._format_status_with_latency(
            result.avatar_command,
            result.latency_ms.get("end_to_end"),
        )
        warnings = _notice("；".join(result.warnings)) if result.warnings else ""
        audio = result.audio_path if result.audio_path else None
        return result.reply_text, status, warnings, audio

    def process(self, user_text: str):
        return self._loop.run_until_complete(self._process_async(user_text, "local-cli"))

    def _format_status(self, cmd: AvatarCommand) -> str:
        return self._format_status_with_latency(cmd, None)

    def _format_status_with_latency(self, cmd: AvatarCommand, latency_ms: float | None) -> str:
        gestures = ", ".join(g.value for g in cmd.gestures) or "idle"
        latency = f"{latency_ms / 1000:.1f}s" if latency_ms is not None else "—"
        items = (
            ("Emotion", cmd.emotion.value),
            ("Expression", cmd.expression.value),
            ("Gesture", gestures),
            ("Voice", f"{cmd.voice_style.value} · {cmd.speaking_rate:.2f}x"),
            ("Intensity", f"{cmd.gesture_intensity:.2f}"),
            ("Latency", latency),
        )
        cells = "".join(
            f'<div class="hai-status-item"><small>{label}</small><strong>{html.escape(value)}</strong></div>'
            for label, value in items
        )
        return f'<div class="hai-status-grid">{cells}</div>'

    def create_interface(self) -> gr.Blocks:
        avatar_provider = self.settings.avatar.provider
        chatbot_avatar_options = (
            {"avatar_images": (None, str(ICON_PATH))}
            if ICON_PATH.exists()
            else {}
        )

        with gr.Blocks(title="HAI · Empathetic Companion", fill_width=True) as demo:
            gr.HTML(
                _brand_header(ICON_PATH, self._provider, self._tts_provider, avatar_provider),
                elem_id="brand-header",
            )

            with gr.Row(elem_id="hero-row"):
                with gr.Column(scale=6, elem_id="hero-copy"):
                    gr.HTML(_hero_copy())
                with gr.Column(scale=5, elem_id="hero-visual"):
                    if HERO_PATH.exists():
                        gr.Image(
                            value=str(HERO_PATH),
                            show_label=False,
                            container=False,
                            interactive=False,
                            buttons=[],
                        )
                    else:
                        gr.HTML('<div class="hai-visual-fallback" aria-label="品牌视觉占位"></div>')

            gr.HTML(
                _section_heading(
                    "Live experience",
                    "现在，和 HAI 聊聊。",
                    "输入一句话，系统会在同一轮中完成理解、回复、语音合成，并驱动角色的表情和动作。",
                ),
                elem_id="experience-heading",
            )

            with gr.Row(elem_id="workspace"):
                with gr.Column(scale=7, elem_id="chat-panel"):
                    gr.HTML('<div class="hai-panel-title"><strong>对话</strong><span>短期上下文已开启</span></div>')
                    chatbot = gr.Chatbot(
                        height=500,
                        show_label=False,
                        container=False,
                        elem_id="conversation",
                        layout="bubble",
                        buttons=["copy"],
                        placeholder="说说你此刻的想法，HAI 会认真听。",
                        **chatbot_avatar_options,
                    )
                    with gr.Row(elem_id="composer-row"):
                        user_input = gr.Textbox(
                            show_label=False,
                            placeholder="输入你想说的话…",
                            lines=2,
                            max_lines=5,
                            scale=7,
                            container=False,
                            elem_id="message-input",
                        )
                        send_btn = gr.Button("发送 ↗", variant="primary", scale=1, elem_id="send-button")
                    with gr.Accordion("语音输入与快捷话题", open=False, elem_id="conversation-tools"):
                        mic_btn = gr.Audio(
                            sources=["microphone"],
                            type="filepath",
                            label="录音转文字",
                            elem_id="voice-input",
                        )
                        gr.Examples(
                            examples=[
                                ["今天发生了一件让我很开心的事。"],
                                ["我最近项目压力很大，不知道该怎么办。"],
                                ["我有点焦虑，可以陪我聊一会儿吗？"],
                                ["请帮我把一个复杂问题讲简单一点。"],
                            ],
                            inputs=[user_input],
                            label="从这些话题开始",
                        )
                    clear_btn = gr.Button("清空本次对话", size="sm", elem_id="clear-button")

                with gr.Column(scale=5, elem_id="avatar-panel"):
                    gr.HTML('<div class="hai-panel-title"><strong>实时角色</strong><span>表情 · 动作 · 口型</span></div>')
                    if avatar_provider == "prometheus":
                        bridge_host = self.settings.avatar.bridge_host
                        browser_host = "127.0.0.1" if bridge_host == "0.0.0.0" else bridge_host
                        bridge_url = f"http://{browser_host}:{self.settings.avatar.bridge_port}/?embed=1"
                        gr.HTML(
                            f'<div id="avatar-stage"><iframe title="HAI Live2D 虚拟角色" src="{bridge_url}" '
                            'allow="autoplay"></iframe></div>'
                        )
                    else:
                        gr.HTML('<div id="avatar-stage" class="hai-avatar-fallback">Avatar 将在真实模式下显示</div>')
                    reply_text = gr.Markdown(
                        "等待你的第一句话…",
                        elem_id="latest-reply",
                        line_breaks=True,
                    )
                    audio_output = gr.Audio(
                        label="回复语音",
                        type="filepath",
                        autoplay=False,
                        editable=False,
                        buttons=["download"],
                        elem_id="reply-audio",
                    )
                    with gr.Accordion("本轮表现", open=True, elem_id="turn-details"):
                        avatar_status = gr.HTML(_initial_status())
                        warnings_output = gr.HTML("")

            gallery_items = [
                (str(image_path), caption)
                for image_path, caption in STORY_IMAGES
                if image_path.exists()
            ]
            gr.HTML(
                _section_heading(
                    "Designed for presence",
                    "让交互多一点温度。",
                    "从情绪判断到声音和动作，视觉与交互使用同一套克制、温暖的表达语言。",
                ),
                elem_id="story-heading",
            )
            if gallery_items:
                gr.Gallery(
                    value=gallery_items,
                    columns=4,
                    rows=1,
                    height=280,
                    object_fit="cover",
                    show_label=False,
                    buttons=["fullscreen"],
                    elem_id="story-gallery",
                )
            gr.HTML(
                """
                <div class="hai-feature-grid">
                <div class="hai-feature"><b>理解上下文</b><span>每个浏览器会话拥有独立短期记忆，清空对话会同步清理后端状态。</span></div>
                <div class="hai-feature"><b>一次推理，多维表达</b><span>单次 LLM 调用同时生成回复与控制字段，再由确定性规则做安全校验。</span></div>
                <div class="hai-feature"><b>真实语音链路</b><span>回复经过 TTS 生成标准 PCM WAV，并与 Live2D 口型和动作保持同轮同步。</span></div>
                </div>
                """,
                elem_id="feature-strip",
            )

            async def respond(user_text: str, history: list, request: gr.Request):
                if not user_text or not user_text.strip():
                    return history, "请先输入一句话。", _notice("请输入内容后再发送。"), "", None
                session_id = request.session_hash or "local-session"
                reply, status, warnings, audio = await self._process_async(user_text, session_id)
                history = list(history or [])
                history.append({"role": "user", "content": user_text})
                if reply:
                    history.append({"role": "assistant", "content": reply})
                latest_reply = reply or "这次没有生成有效回复，请再试一次。"
                return history, latest_reply, status, warnings, audio

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
                api_name="respond",
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
                return [], "等待你的第一句话…", _initial_status(), "", None

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
        allowed_paths = [str(BRAND_ASSET_DIR)] if BRAND_ASSET_DIR.exists() else None
        demo.launch(
            server_name=self.settings.app.server_name,
            server_port=port or self.settings.app.server_port,
            favicon_path=str(ICON_PATH) if ICON_PATH.exists() else None,
            allowed_paths=allowed_paths,
            footer_links=[],
            css_paths=STYLES_PATH,
        )


def create_app(settings: Settings | None = None) -> gr.Blocks:
    return GradioApp(settings).create_interface()


if __name__ == "__main__":
    GradioApp().run()
