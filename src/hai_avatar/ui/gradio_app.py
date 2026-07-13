"""Placeholder for the Phase 3 Gradio UI."""

import gradio as gr
from pathlib import Path
import yaml
from hai_avatar.services.pipeline_service import PipelineService
from hai_avatar.schemas import AvatarCommand
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.llm.mock_provider import MockLLMProvider
from hai_avatar.tts.mock_provider import MockTTSProvider
from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.config import Settings


class GradioApp:
    def __init__(self):
        
        with open(Path("./config/default.yaml"), "r") as f:
            config_raw = yaml.safe_load(f)
        settings = Settings(**config_raw)
        
        self.service = PipelineService(
            settings=settings,
            llm_provider=MockLLMProvider(),
            tts_provider=MockTTSProvider(),
            avatar_controller=MockAvatarController(),
            action_planner=ActionPlanner()
        )

    def process(self, user_text: str):
        if not user_text or not user_text.strip():
            return "", "请输出内容", "", None

        import asyncio
        result = asyncio.run(self.service.process(user_text))

        status = self._format_status(result.avatar_command)
        warnings = "\n".join(result.warnings) if result.warnings else ""
        audio = result.audio_path if result.audio_path else None

        return result.reply_text, status, warnings, audio

    def _format_status(self, cmd: AvatarCommand) -> str:
        gestures = ", ".join([g.value for g in cmd.gestures])
        return f"""情绪: {cmd.emotion.value}
            表情: {cmd.expression.value}
            手势: {gestures}
            语音风格: {cmd.voice_style.value}"""

    def create_interface(self):
        with gr.Blocks(title="V Avatar") as demo:
            gr.Markdown("# V Avatar")

            with gr.Row():
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(height=400)
                    user_input = gr.Textbox(
                        label="输入消息",
                        placeholder="输入你想说的话...",
                        lines=2
                    )
                    with gr.Row():
                        send_btn = gr.Button("发送", variant="primary")
                        clear_btn = gr.Button("清空对话")

                with gr.Column(scale=1):
                    reply_text = gr.Textbox(label="AI回复", lines=4, interactive=False)
                    audio_output = gr.Audio(label="语音输出", type="filepath")
                    avatar_status = gr.Textbox(label="Avatar状态", lines=4, interactive=False)
                    warnings_output = gr.Textbox(label="系统提示", lines=2, interactive=False)

            def respond(user_text, history):
                if not user_text or not user_text.strip():
                    return history, "", "请输内容", "", None

                history.append({"role": "user", "content": user_text})
                reply, status, warnings, audio = self.process(user_text)
                history.append({"role": "assistant", "content": reply})
                return history, reply, status, warnings, audio

            send_btn.click(
                fn=respond,
                inputs=[user_input, chatbot],
                outputs=[chatbot, reply_text, avatar_status, warnings_output, audio_output]
            ).then(fn=lambda: "", inputs=[], outputs=[user_input])

            user_input.submit(
                fn=respond,
                inputs=[user_input, chatbot],
                outputs=[chatbot, reply_text, avatar_status, warnings_output, audio_output]
            ).then(fn=lambda: "", inputs=[], outputs=[user_input])

            def clear_all():
                return [], "", "", "", None

            clear_btn.click(
                fn=clear_all,
                inputs=[],
                outputs=[chatbot, reply_text, avatar_status, warnings_output, audio_output]
            )

            gr.Examples(
                examples=[
                    ["你好"],
                    ["我最近压力很大"],
                    ["能解释一下吗"],
                    ["谢谢你的帮助"],
                    ["再见"]
                ],
                inputs=[user_input],
                label="示例"
            )

        return demo

    def run(self, port=7860):
        demo = self.create_interface()
        demo.launch(server_name="0.0.0.0", server_port=port)


def create_app():
    """Phase 3 will provide the real Gradio Blocks application."""
    app = GradioApp()
    return app.create_interface()

if __name__ == "__main__":
    app = GradioApp()
    app.run()
    
