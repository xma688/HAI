"""Phase 3 placeholder for the Gradio app runner."""

from hai_avatar.ui.gradio_app import create_app


if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
