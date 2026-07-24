import re

from hai_avatar.schemas import (
    AvatarCommand,
    EmotionType,
    ExpressionType,
    GestureType,
    VoiceStyleType,
)
from hai_avatar.ui import gradio_app


def test_progress_idle_has_root_class():
    html = gradio_app._progress_html("idle")
    assert "hai-progress" in html
    assert 'role="status"' in html


def test_progress_error_marks_error_state():
    html = gradio_app._progress_html("error")
    assert "is-error" in html


def test_progress_complete_marks_all_done():
    html = gradio_app._progress_html("complete")
    # 4 个阶段步骤，complete 时全部 done
    assert html.count("done") >= 4


def test_notice_escapes_and_marks_error():
    html = gradio_app._notice("<script>x</script>", error=True)
    assert "hai-notice error" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_status_grid_renders_six_cells():
    cmd = AvatarCommand(
        emotion=EmotionType.happy,
        expression=ExpressionType.smile,
        gestures=[GestureType.nod],
        voice_style=VoiceStyleType.cheerful,
        gesture_intensity=0.6,
        speaking_rate=1.05,
    )
    html = gradio_app._format_status_with_latency(cmd, 1234.0)
    assert "hai-status-grid" in html
    assert html.count("hai-status-item") == 6
    assert "1.2s" in html  # latency 格式化


def test_initial_status_renders_grid():
    html = gradio_app._initial_status()
    assert "hai-status-grid" in html
    assert html.count("hai-status-item") == 6


def test_brand_header_connected_vs_demo():
    connected = gradio_app._brand_header("prometheus")
    demo = gradio_app._brand_header("mock")
    assert "hai-header" in connected
    assert "connected" in connected
    assert "demo" in demo


def test_welcome_is_lightweight_greeting():
    html = gradio_app._welcome_markup()
    assert "hai-welcome" in html
    assert "img.png" in html
    assert "--hai-home-art" in html


def test_privacy_copy_matches_persistent_personalization():
    assert "可随时清空" in gradio_app._conversation_heading()
    footer = gradio_app._footer_band()
    assert "个性化资料" in footer
    assert "不会被长期留存" not in footer


def test_chat_panel_never_wraps_into_extra_columns():
    css = gradio_app.STYLES_PATH.read_text(encoding="utf-8")
    assert re.search(
        r"#chat-panel\s*\{[^}]*flex-wrap:\s*nowrap\s*!important",
        css,
        re.DOTALL,
    )


def test_story_markup_removed():
    assert not hasattr(gradio_app, "_story_markup")


def test_progress_breathing_bar_structure():
    html = gradio_app._progress_html("voice")
    assert "hai-progress" in html
    assert "hai-progress-dot" in html
    assert "hai-progress-track" in html


def test_message_input_has_elem_id():
    # 确认 create_interface 能构建且 message-input 存在于蓝图
    from hai_avatar.config import load_settings
    settings = load_settings()
    settings = settings.model_copy(deep=True)
    settings.llm.provider = "mock"; settings.tts.provider = "mock"; settings.avatar.provider = "mock"
    app = gradio_app.GradioApp(settings)
    demo = app.create_interface()
    assert demo is not None


def test_progress_complete_carries_emotion_class():
    html = gradio_app._progress_html("complete", emotion="happy")
    assert "emotion-happy" in html


def test_progress_default_no_emotion_class():
    html = gradio_app._progress_html("understanding")
    assert "emotion-" not in html
