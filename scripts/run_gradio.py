"""Run the configured Gradio and optional Prometheus bridge services."""

from hai_avatar.ui.gradio_app import GradioApp


if __name__ == "__main__":
    GradioApp().run()
