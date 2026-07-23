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
