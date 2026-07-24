"""Gradio UI for the HAI companion experience."""

from __future__ import annotations

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

ILLUSTRATION_PATH = PROJECT_ROOT / "img.png"
STYLES_PATH = Path(__file__).with_name("styles.css")

_PROGRESS_STAGES = (
    ("understanding", "理解", "正在理解你的话"),
    ("reply", "回复", "文字回应已准备好"),
    ("voice", "声音", "正在生成这一轮语音"),
    ("performance", "表演", "正在准备表情与动作"),
)


def _file_url(path: Path) -> str:
    return f"/gradio_api/file={html.escape(path.resolve().as_posix(), quote=True)}"


def _brand_header(avatar_provider: str) -> str:
    connected = avatar_provider == "prometheus"
    status_class = "connected" if connected else "demo"
    status_text = "角色已连接" if connected else "演示模式"
    return f"""
    <header class="hai-header" role="banner">
      <div class="hai-brand">
        <span class="hai-brand-mark" aria-hidden="true">H</span>
        <span class="hai-brand-copy"><b>HAI</b><small>安静的 AI 陪伴</small></span>
      </div>
      <span class="hai-status-chip {status_class}"><i class="hai-dot" aria-hidden="true"></i>{status_text}</span>
    </header>
    """


def _welcome_markup() -> str:
    illustration_url = _file_url(ILLUSTRATION_PATH)
    return f"""
    <div id="hai-welcome" class="hai-welcome" style="--hai-home-art:url('{illustration_url}')">
      <div class="hai-welcome-copy">
        <span class="hai-welcome-eyebrow"><i aria-hidden="true"></i> Emotion-aware companion</span>
        <h1 class="hai-welcome-line">今晚，慢慢说。</h1>
        <p class="hai-welcome-note">让声音、表情和动作陪你把这一刻说完整。</p>
      </div>
      <div class="hai-welcome-meta" aria-label="体验能力">
        <span>Live2D 实时陪伴</span><span>情绪感知</span><span>自然语音</span>
      </div>
    </div>
    """


def _avatar_stage_markup(settings: Settings) -> str:
    if settings.avatar.provider == "prometheus":
        bridge_host = settings.avatar.bridge_host
        browser_host = "127.0.0.1" if bridge_host == "0.0.0.0" else bridge_host
        bridge_url = f"http://{browser_host}:{settings.avatar.bridge_port}/?embed=1"
        content = (
            f'<iframe title="HAI Live2D 虚拟角色" src="{bridge_url}" allow="autoplay"></iframe>'
        )
        mode = "live"
        state = "Live2D · 已连接"
    else:
        content = (
            '<div class="hai-stage-empty"><span class="hai-stage-moon" aria-hidden="true">☾</span>'
            '<span>Live2D Avatar</span><small>请启用真实角色模式</small></div>'
        )
        mode = "static"
        state = "Avatar · 未连接"
    return f"""
    <div class="hai-panel-head">
      <div class="hai-panel-title"><span>Companion</span><strong>Live2D Avatar</strong></div>
      <span class="hai-stage-state">{state}</span>
    </div>
    <div id="avatar-stage" class="hai-avatar-stage {mode}">
      <div class="hai-stage-glow" aria-hidden="true"></div>
      {content}
      <div class="hai-waveform {mode}" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
      <div class="hai-stage-caption"><span>我在，慢慢说。</span><small>表情 · 动作 · 口型</small></div>
    </div>
    """


def _conversation_heading() -> str:
    return """
    <div class="hai-panel-head hai-conversation-heading">
      <div class="hai-panel-title"><span>Conversation</span><strong>我们的对话</strong></div>
      <span class="hai-privacy-chip">会话记忆 · 可随时清空</span>
    </div>
    """


def _footer_band() -> str:
    return """
    <footer class="hai-footer" role="contentinfo">
      <div class="hai-footer-brand">
        <span class="hai-brand-mark" aria-hidden="true">H</span>
        <div><b>HAI</b><small>安静的 AI 陪伴 · Emotion-aware companion</small></div>
      </div>
      <p class="hai-footer-note">清空会话会移除短期上下文；个性化资料会按系统设置保留。</p>
    </footer>
    """


def _progress_html(stage: str = "idle", emotion: str = "") -> str:
    if stage == "error":
        return (
            '<div class="hai-progress is-error" role="status" aria-live="polite" aria-busy="false">'
            '<span class="hai-progress-dot" aria-hidden="true"></span>'
            '<div class="hai-progress-copy"><b>这轮回应没有完成</b>'
            '<span>你的输入仍然保留，可以重新发送。</span></div>'
            '<div class="hai-progress-track"><i style="width:100%"></i></div></div>'
        )
    stage_names = [name for name, _, _ in _PROGRESS_STAGES]
    current_index = stage_names.index(stage) if stage in stage_names else -1
    is_complete = stage == "complete"
    total = len(_PROGRESS_STAGES)
    if is_complete:
        message = "这轮回应已经完成"
        done_labels = [label for _, label, _ in _PROGRESS_STAGES]
        percent = 100
    elif current_index >= 0:
        message = _PROGRESS_STAGES[current_index][2]
        done_labels = [label for _, label, _ in _PROGRESS_STAGES[: current_index + 1]]
        percent = int((current_index + 1) / total * 100)
    else:
        message = "准备好听你说"
        done_labels = []
        percent = 0
    busy = "true" if current_index >= 0 and not is_complete else "false"
    # done 标记：complete 或已完成阶段用于测试断言与视觉
    done_markup = "".join(f'<span class="done">{label}</span>' for label in done_labels)
    emotion_class = f" emotion-{html.escape(emotion)}" if (is_complete and emotion) else ""
    return f"""
    <div class="hai-progress{emotion_class}" role="status" aria-live="polite" aria-busy="{busy}">
      <span class="hai-progress-dot" aria-hidden="true"></span>
      <div class="hai-progress-copy"><b>{message}</b><span class="hai-progress-stages">{done_markup}</span></div>
      <div class="hai-progress-track"><i style="width:{percent}%"></i></div>
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
    return f'<div class="hai-notice{kind}" role="alert">{html.escape(message)}</div>'


def _format_status_with_latency(cmd: AvatarCommand, latency_ms: float | None) -> str:
    gestures = ", ".join(gesture.value for gesture in cmd.gestures) or "idle"
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


def _transcribe_audio(audio_path: str | None, settings: Settings) -> str:
    if not audio_path or not os.path.exists(audio_path):
        return ""
    try:
        from openai import OpenAI

        api_key = os.getenv(settings.llm.api_key_env, "")
        if not api_key:
            logger.warning("No API key for transcription; skipping ASR")
            return ""
        model = os.getenv("ASR_MODEL", "whisper-1")
        mime_type = mimetypes.guess_type(audio_path)[0] or "application/octet-stream"
        client = OpenAI(api_key=api_key, base_url=settings.llm.base_url)
        with open(audio_path, "rb") as file_handle:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=(os.path.basename(audio_path), file_handle, mime_type),
            )
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

    async def _process_async(
        self,
        user_text: str,
        session_id: str = "default",
        progress_callback=None,
    ):
        if not user_text or not user_text.strip():
            return "", _initial_status(), _notice("请输入内容后再发送。", error=True), None, "neutral"
        try:
            result = await self.service.process(
                user_text,
                user_id=session_id,
                progress_callback=progress_callback,
            )
        except PipelineError as exc:
            return "", _initial_status(), _notice(str(exc), error=True), None, "neutral"
        except Exception:
            logger.exception("Gradio request failed for session=%s", session_id)
            return "", _initial_status(), _notice("请求处理失败，请稍后重试。", error=True), None, "neutral"
        status = self._format_status_with_latency(
            result.avatar_command,
            result.latency_ms.get("end_to_end"),
        )
        warnings = _notice("；".join(result.warnings)) if result.warnings else ""
        return result.reply_text, status, warnings, result.audio_path, result.avatar_command.emotion.value

    def process(self, user_text: str):
        return self._loop.run_until_complete(self._process_async(user_text, "local-cli"))

    def _format_status(self, cmd: AvatarCommand) -> str:
        return _format_status_with_latency(cmd, None)

    def _format_status_with_latency(self, cmd: AvatarCommand, latency_ms: float | None) -> str:
        return _format_status_with_latency(cmd, latency_ms)

    def create_interface(self) -> gr.Blocks:
        with gr.Blocks(title="HAI · 安静的 AI 陪伴", fill_width=True) as demo:
            gr.HTML(_brand_header(self.settings.avatar.provider), elem_id="brand-header")
            welcome_section = gr.HTML(_welcome_markup(), elem_id="welcome-section")

            with gr.Column(elem_id="experience-shell"):
                with gr.Row(elem_id="workspace"):
                    with gr.Column(scale=6, elem_id="avatar-panel"):
                        gr.HTML(_avatar_stage_markup(self.settings))

                    with gr.Column(scale=6, elem_id="chat-panel"):
                        gr.HTML(_conversation_heading())
                        progress_output = gr.HTML(_progress_html(), elem_id="turn-progress")
                        chatbot = gr.Chatbot(
                            height=430,
                            show_label=False,
                            container=False,
                            elem_id="conversation",
                            layout="bubble",
                            buttons=["copy"],
                            placeholder="说点什么，我在听。",
                            group_consecutive_messages=True,
                        )
                        with gr.Row(elem_id="composer-row"):
                            user_input = gr.Textbox(
                                show_label=False,
                                placeholder="说点什么，我在听。",
                                lines=2,
                                max_lines=5,
                                scale=8,
                                container=False,
                                elem_id="message-input",
                            )
                            send_btn = gr.Button(
                                "发送 ↗",
                                variant="primary",
                                scale=1,
                                elem_id="send-button",
                            )

                        with gr.Row(elem_id="quick-prompts"):
                            prompt_one = gr.Button("最近有点累", size="sm")
                            prompt_two = gr.Button("陪我聊一会儿", size="sm")
                            prompt_three = gr.Button("帮我理清思路", size="sm")

                        warnings_output = gr.HTML("", elem_id="turn-warnings")

                        with gr.Row(elem_id="conversation-actions"):
                            clear_request = gr.Button("清空本次对话", size="sm", elem_id="clear-button")

                with gr.Column(elem_id="voice-lane"):
                    audio_output = gr.Audio(
                        label="本轮语音",
                        type="filepath",
                        autoplay=False,
                        editable=False,
                        buttons=["download"],
                        visible=False,
                        elem_id="reply-audio",
                    )
                    with gr.Accordion("使用语音输入", open=False, elem_id="voice-tools"):
                        mic_btn = gr.Audio(
                            sources=["microphone"],
                            type="filepath",
                            label="录音结束后自动转成文字",
                            elem_id="voice-input",
                        )

                with gr.Accordion("本轮表现 · 技术诊断", open=False, elem_id="turn-details"):
                    gr.HTML(
                        f'<div class="hai-runtime"><span>LLM · {html.escape(self._provider)}</span>'
                        f'<span>TTS · {html.escape(self._tts_provider)}</span>'
                        f'<span>Avatar · {html.escape(self.settings.avatar.provider)}</span></div>'
                    )
                    avatar_status = gr.HTML(_initial_status())

                gr.HTML(_footer_band(), elem_id="footer-section")

            with gr.Group(visible=False, elem_id="clear-dialog") as clear_dialog:
                gr.HTML(
                    """
                    <div class="hai-dialog-copy"><span>Clear conversation</span>
                    <h3>清空这次对话？</h3>
                    <p>短期上下文、角色状态和动作冷却会一起清除；个性化资料仍会保留。</p></div>
                    """
                )
                with gr.Row(elem_id="clear-dialog-actions"):
                    clear_cancel = gr.Button("取消", elem_id="clear-cancel")
                    clear_confirm = gr.Button("确认清空", variant="stop", elem_id="clear-confirm")

            async def respond(user_text: str, history: list, request: gr.Request):
                if not user_text or not user_text.strip():
                    yield (
                        history,
                        _progress_html("error"),
                        gr.skip(),
                        _notice("请输入内容后再发送。", error=True),
                        gr.update(value=None, visible=False),
                        gr.skip(),
                        gr.update(value="发送 ↗", interactive=True),
                        user_text,
                    )
                    return

                session_id = request.session_hash or "local-session"
                next_history = list(history or [])
                next_history.append({"role": "user", "content": user_text.strip()})
                progress_queue: asyncio.Queue = asyncio.Queue()

                async def report_progress(stage: str, payload: dict):
                    await progress_queue.put((stage, payload))

                task = asyncio.create_task(
                    self._process_async(user_text, session_id, report_progress)
                )
                reply_added = False
                yield (
                    next_history,
                    _progress_html("understanding"),
                    gr.skip(),
                    "",
                    gr.update(value=None, visible=False),
                    gr.update(visible=False),
                    gr.update(value="回应中…", interactive=False),
                    "",
                )

                while not task.done():
                    try:
                        stage, payload = await asyncio.wait_for(progress_queue.get(), timeout=0.15)
                    except TimeoutError:
                        continue
                    if stage == "reply" and payload.get("reply_text") and not reply_added:
                        next_history.append(
                            {"role": "assistant", "content": payload["reply_text"]}
                        )
                        reply_added = True
                    yield (
                        next_history,
                        _progress_html(stage),
                        gr.skip(),
                        "",
                        gr.update(value=None, visible=False),
                        gr.update(visible=False),
                        gr.update(value="回应中…", interactive=False),
                        "",
                    )

                reply, status, warnings, audio, emotion = await task
                if reply and not reply_added:
                    next_history.append({"role": "assistant", "content": reply})
                    reply_added = True
                final_stage = "complete" if reply else "error"
                yield (
                    next_history,
                    _progress_html(final_stage, emotion=emotion if reply else ""),
                    status,
                    warnings,
                    gr.update(value=audio, visible=bool(audio)),
                    gr.update(visible=False),
                    gr.update(value="发送 ↗", interactive=True),
                    "",
                )

            def transcribe(audio_path: str | None):
                if not audio_path:
                    return gr.skip(), _notice("请先完成一段录音。", error=True)
                text = _transcribe_audio(audio_path, self.settings)
                if not text:
                    return gr.skip(), _notice("没听清，请再试一次。", error=True)
                return text, ""

            send_outputs = [
                chatbot,
                progress_output,
                avatar_status,
                warnings_output,
                audio_output,
                welcome_section,
                send_btn,
                user_input,
            ]
            send_btn.click(
                fn=respond,
                inputs=[user_input, chatbot],
                outputs=send_outputs,
                api_name="respond",
            ).then(
                fn=None, js="() => { const el=document.querySelector('#message-input textarea'); if(el) el.focus(); }",
            )
            user_input.submit(
                fn=respond,
                inputs=[user_input, chatbot],
                outputs=send_outputs,
            ).then(
                fn=None, js="() => { const el=document.querySelector('#message-input textarea'); if(el) el.focus(); }",
            )

            prompt_one.click(lambda: "最近有点累，想找个人说说。", outputs=user_input).then(
                fn=None, js="() => { const el=document.querySelector('#message-input textarea'); if(el){ el.focus(); el.setSelectionRange(el.value.length, el.value.length);} }",
            )
            prompt_two.click(lambda: "可以陪我聊一会儿吗？", outputs=user_input).then(
                fn=None, js="() => { const el=document.querySelector('#message-input textarea'); if(el){ el.focus(); el.setSelectionRange(el.value.length, el.value.length);} }",
            )
            prompt_three.click(lambda: "我脑子有点乱，能帮我理清思路吗？", outputs=user_input).then(
                fn=None, js="() => { const el=document.querySelector('#message-input textarea'); if(el){ el.focus(); el.setSelectionRange(el.value.length, el.value.length);} }",
            )
            mic_btn.stop_recording(
                fn=transcribe,
                inputs=mic_btn,
                outputs=[user_input, warnings_output],
            )

            clear_request.click(
                lambda: gr.update(visible=True),
                outputs=clear_dialog,
            )
            clear_cancel.click(
                lambda: gr.update(visible=False),
                outputs=clear_dialog,
            )

            async def clear_session(request: gr.Request):
                session_id = request.session_hash or "local-session"
                await self.service.clear_session(session_id)
                return (
                    [],
                    _progress_html(),
                    _initial_status(),
                    "",
                    gr.update(value=None, visible=False),
                    gr.update(visible=False),
                )

            clear_confirm.click(
                fn=clear_session,
                inputs=[],
                outputs=[
                    chatbot,
                    progress_output,
                    avatar_status,
                    warnings_output,
                    audio_output,
                    clear_dialog,
                ],
            )

            demo.load(
                fn=None,
                js="""
                () => {
                  const focus = () => {
                    const el = document.querySelector('#message-input textarea');
                    if (el) el.focus({ preventScroll: true });
                  };
                  setTimeout(focus, 300);
                }
                """,
            )

        return demo.queue(default_concurrency_limit=1, max_size=16)

    def run(self, port: int | None = None) -> None:
        if self.settings.avatar.provider == "prometheus":
            from hai_avatar.avatar.bridge_server import start_avatar_bridge_server

            output_dir = self.settings.avatar.prometheus_output_dir
            if not output_dir.is_absolute():
                output_dir = PROJECT_ROOT / output_dir
            start_avatar_bridge_server(
                output_dir,
                host=self.settings.avatar.bridge_host,
                port=self.settings.avatar.bridge_port,
            )
        demo = self.create_interface()
        allowed_paths = [str(ILLUSTRATION_PATH.resolve())] if ILLUSTRATION_PATH.exists() else []
        demo.launch(
            server_name=self.settings.app.server_name,
            server_port=port or self.settings.app.server_port,
            allowed_paths=allowed_paths or None,
            footer_links=[],
            css_paths=STYLES_PATH,
        )


def create_app(settings: Settings | None = None) -> gr.Blocks:
    return GradioApp(settings).create_interface()


if __name__ == "__main__":
    GradioApp().run()
