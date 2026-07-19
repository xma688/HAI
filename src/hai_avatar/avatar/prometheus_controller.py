"""Prometheus Avatar SDK bridge controller.

The Prometheus SDK runs in the browser, so this controller does not import the
TypeScript package directly. It writes a small local HTML bridge and a state
file that can be opened in a browser to render a Live2D avatar with the latest
pipeline output.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hai_avatar.avatar.base import AvatarController

logger = logging.getLogger(__name__)


PROMETHEUS_EMOTION_MAP = {
    "neutral": "neutral",
    "happy": "happy",
    "supportive": "happy",
    "thoughtful": "thinking",
    "confused": "thinking",
    "surprised": "surprised",
    "serious": "neutral",
    "apologetic": "sad",
    "smile": "happy",
    "soft_smile": "happy",
    "thinking": "thinking",
    "concerned": "sad",
}


class PrometheusAvatarController(AvatarController):
    """Write Prometheus-compatible browser bridge state from Python commands."""

    def __init__(self, output_dir: Path, model_url: str) -> None:
        self.output_dir = output_dir
        self.model_url = model_url
        self.state_path = self.output_dir / "avatar-state.js"
        self.html_path = self.output_dir / "index.html"
        self.state: dict[str, Any] = {
            "connected": False,
            "reply_text": "",
            "expression": "neutral",
            "prometheus_emotion": "neutral",
            "gestures": [],
            "voice_style": "neutral",
            "audio_path": None,
            "speaking": False,
            "events": [],
            "model_url": self.model_url,
            "updated_at": None,
        }

    async def connect(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state["connected"] = True
        self._event("connected")
        self._write_bridge()
        logger.info("Prometheus bridge ready at %s", self.html_path)

    async def set_reply_text(self, reply_text: str, voice_style: str = "neutral") -> None:
        self.state["reply_text"] = reply_text
        self.state["voice_style"] = voice_style
        self._event("reply_text updated")
        self._write_bridge()

    async def set_expression(self, expression: str) -> None:
        self.state["expression"] = expression
        self.state["prometheus_emotion"] = PROMETHEUS_EMOTION_MAP.get(expression, "neutral")
        self._event(f"expression -> {expression}")
        self._write_bridge()

    async def trigger_gesture(self, gesture: str) -> None:
        self.state.setdefault("gestures", []).append(gesture)
        self._event(f"gesture -> {gesture}")
        self._write_bridge()

    async def play_audio(self, audio_path: str) -> None:
        self.state["audio_path"] = audio_path
        self._event(f"audio -> {audio_path}")
        self._write_bridge()

    async def start_speaking(self) -> None:
        self.state["speaking"] = True
        self._event("speaking started")
        self._write_bridge()

    async def stop_speaking(self) -> None:
        self.state["speaking"] = False
        self._event("speaking stopped")
        self._write_bridge()

    async def reset_to_idle(self) -> None:
        self._event("returned to idle")
        self._write_bridge()

    def _event(self, message: str) -> None:
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.state.setdefault("events", []).append(message)
        self.state["events"] = self.state["events"][-20:]
        print(f"[PrometheusBridge] {message}")

    def _write_bridge(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            "window.HAI_AVATAR_STATE = "
            + json.dumps(self.state, ensure_ascii=False, indent=2)
            + ";\n",
            encoding="utf-8",
        )
        self.html_path.write_text(self._html(), encoding="utf-8")

    def _html(self) -> str:
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>HAI Prometheus Avatar Bridge</title>
  <script src="https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js"></script>
  <script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
  <style>
    :root { color-scheme: dark; font-family: Inter, "Microsoft YaHei", sans-serif; }
    body { margin: 0; min-height: 100vh; background: #101014; color: #f4f4f5; display: grid; grid-template-columns: minmax(420px, 1fr) 380px; }
    #avatar { width: 100%; height: 100vh; background: #08080b; }
    aside { padding: 20px; border-left: 1px solid #2a2a32; background: #17171d; overflow: auto; }
    h1 { font-size: 20px; margin: 0 0 14px; }
    .row { margin: 12px 0; }
    .label { color: #a1a1aa; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    .value { margin-top: 4px; line-height: 1.5; word-break: break-word; }
    .pill { display: inline-block; padding: 3px 8px; border: 1px solid #3f3f46; border-radius: 999px; margin: 2px; }
    button { border: 0; padding: 10px 14px; border-radius: 8px; background: #00d4aa; color: #07100e; font-weight: 700; cursor: pointer; }
    pre { white-space: pre-wrap; background: #0d0d11; padding: 10px; border-radius: 8px; color: #d4d4d8; }
  </style>
  <script src="./avatar-state.js"></script>
</head>
<body>
  <div id="avatar"></div>
  <aside>
    <h1>HAI Avatar Bridge</h1>
    <button id="speakBtn">Speak latest reply</button>
    <div class="row"><div class="label">Reply</div><div id="reply" class="value"></div></div>
    <div class="row"><div class="label">Expression</div><div id="expression" class="value"></div></div>
    <div class="row"><div class="label">Gestures</div><div id="gestures" class="value"></div></div>
    <div class="row"><div class="label">Voice / Audio</div><div id="audio" class="value"></div></div>
    <div class="row"><div class="label">Events</div><pre id="events"></pre></div>
  </aside>
  <script type="module">
    import { createAvatar } from 'https://esm.sh/@prometheusavatar/core@0.8.0';

    const state = window.HAI_AVATAR_STATE || {};
    document.getElementById('reply').textContent = state.reply_text || '(no reply yet)';
    document.getElementById('expression').textContent = `${state.expression} -> ${state.prometheus_emotion}`;
    document.getElementById('gestures').innerHTML = (state.gestures || []).map(g => `<span class="pill">${g}</span>`).join(' ') || '(none)';
    document.getElementById('audio').textContent = `${state.voice_style || 'neutral'} | ${state.audio_path || '(no audio)'}`;
    document.getElementById('events').textContent = (state.events || []).join('\\n');

    let avatar = null;
    try {
      avatar = await createAvatar({
        container: document.getElementById('avatar'),
        modelUrl: state.model_url,
        ttsOptions: { lang: 'zh-CN', rate: 1.0, pitch: 1.0, volume: 1.0 },
        backgroundColor: 0x08080b,
      });
      avatar.setEmotion(state.prometheus_emotion || 'neutral');
      if (state.reply_text) {
        avatar.processText(state.reply_text);
      }
    } catch (error) {
      document.getElementById('avatar').innerHTML = `<pre style="padding:20px;color:#fca5a5">Prometheus SDK failed to load. Check browser network/CDN access and Live2D runtime scripts.\\n${error}</pre>`;
      console.error(error);
    }

    document.getElementById('speakBtn').onclick = async () => {
      if (avatar && state.reply_text) {
        avatar.setEmotion(state.prometheus_emotion || 'neutral');
        await avatar.speak(state.reply_text);
      }
    };
  </script>
</body>
</html>
"""
