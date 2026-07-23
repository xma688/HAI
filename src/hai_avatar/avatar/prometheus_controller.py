"""Prometheus Avatar SDK bridge controller.

The Prometheus SDK runs in the browser, so this controller does not import the
TypeScript package directly. It writes a small local HTML bridge and a state
file that can be opened in a browser to render a Live2D avatar with the latest
pipeline output.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
import wave
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
        self.state_json_path = self.output_dir / "avatar-state.json"
        self.html_path = self.output_dir / "index.html"
        self.state: dict[str, Any] = {
            "connected": False,
            "turn_id": None,
            "reply_text": "",
            "expression": "neutral",
            "prometheus_emotion": "neutral",
            "gestures": [],
            "gesture_intensity": 0.5,
            "voice_style": "neutral",
            "audio_path": None,
            "audio_url": None,
            "audio_duration_ms": 0,
            "speaking": False,
            "events": [],
            "model_url": self.model_url,
            "updated_at": None,
        }
        self._playback_task: asyncio.Task[None] | None = None
        self._reset_after_playback = False
        self._write_bridge()

    async def connect(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state["connected"] = True
        self._event("connected")
        self._write_bridge()
        logger.info("Prometheus bridge ready at %s", self.html_path)

    async def set_reply_text(self, reply_text: str, voice_style: str = "neutral") -> None:
        self._cancel_playback_task()
        self.state["turn_id"] = uuid.uuid4().hex
        self.state["reply_text"] = reply_text
        self.state["voice_style"] = voice_style
        self.state["gestures"] = []
        self.state["gesture_intensity"] = 0.5
        self.state["audio_path"] = None
        self.state["audio_url"] = None
        self.state["audio_duration_ms"] = 0
        self.state["speaking"] = False
        self._reset_after_playback = False
        self._event("reply_text updated")
        self._write_bridge()

    async def set_expression(self, expression: str) -> None:
        self.state["expression"] = expression
        self.state["prometheus_emotion"] = PROMETHEUS_EMOTION_MAP.get(expression, "neutral")
        self._event(f"expression -> {expression}")
        self._write_bridge()

    async def trigger_gesture(self, gesture: str, intensity: float = 0.5) -> None:
        self.state.setdefault("gestures", []).append(gesture)
        self.state["gesture_intensity"] = max(0.0, min(1.0, intensity))
        self._event(f"gesture -> {gesture} ({self.state['gesture_intensity']:.2f})")
        self._write_bridge()

    async def play_audio(self, audio_path: str) -> None:
        source = Path(audio_path)
        if not source.exists():
            raise FileNotFoundError(f"Avatar audio file not found: {source}")
        audio_dir = self.output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        destination = audio_dir / f"{uuid.uuid4().hex}{source.suffix.lower() or '.wav'}"
        shutil.copy2(source, destination)
        self._cleanup_audio(audio_dir)
        duration_ms = self._audio_duration_ms(destination)
        self.state["audio_path"] = str(destination)
        self.state["audio_url"] = f"./audio/{destination.name}"
        self.state["audio_duration_ms"] = duration_ms
        self._event(f"audio ready -> {destination.name}")
        self._write_bridge()
        if duration_ms:
            turn_id = self.state.get("turn_id")
            self._playback_task = asyncio.create_task(
                self._finish_playback(turn_id, duration_ms / 1000),
                name=f"avatar-playback-{turn_id or 'unknown'}",
            )

    async def start_speaking(self) -> None:
        self.state["speaking"] = True
        self._event("speaking started")
        self._write_bridge()

    async def stop_speaking(self) -> None:
        if self._playback_task and not self._playback_task.done():
            return
        self.state["speaking"] = False
        self._event("speaking stopped")
        self._write_bridge()

    async def reset_to_idle(self) -> None:
        if self._playback_task and not self._playback_task.done():
            self._reset_after_playback = True
            return
        self._apply_idle_state()
        self._event("returned to idle")
        self._write_bridge()

    def _apply_idle_state(self) -> None:
        self.state["expression"] = "neutral"
        self.state["prometheus_emotion"] = "neutral"
        self.state["gestures"] = []
        self.state["gesture_intensity"] = 0.5
        self.state["speaking"] = False

    async def _finish_playback(self, turn_id: str | None, duration_seconds: float) -> None:
        """Finish browser playback without blocking the response request."""

        try:
            await asyncio.sleep(duration_seconds)
            if self.state.get("turn_id") != turn_id:
                return
            self.state["speaking"] = False
            self._event("speaking stopped")
            if self._reset_after_playback:
                self._apply_idle_state()
                self._event("returned to idle")
            self._write_bridge()
        except asyncio.CancelledError:
            return
        finally:
            if asyncio.current_task() is self._playback_task:
                self._playback_task = None
                self._reset_after_playback = False

    def _cancel_playback_task(self) -> None:
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
        self._playback_task = None
        self._reset_after_playback = False

    async def clear_session_state(self) -> None:
        """Remove reply and media state in addition to returning to idle."""

        self._cancel_playback_task()
        self.state.update(
            {
                "turn_id": None,
                "reply_text": "",
                "expression": "neutral",
                "prometheus_emotion": "neutral",
                "gestures": [],
                "gesture_intensity": 0.5,
                "voice_style": "neutral",
                "audio_path": None,
                "audio_url": None,
                "audio_duration_ms": 0,
                "speaking": False,
                "events": [],
            }
        )
        self._event("session cleared")
        self._write_bridge()

    @staticmethod
    def _audio_duration_ms(audio_path: Path) -> int:
        if audio_path.suffix.lower() != ".wav":
            return 0
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                return int(wav_file.getnframes() / float(wav_file.getframerate()) * 1000)
        except (wave.Error, EOFError, ZeroDivisionError):
            return 0

    @staticmethod
    def _cleanup_audio(audio_dir: Path, keep_latest: int = 20) -> None:
        files = sorted(
            (path for path in audio_dir.iterdir() if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale_path in files[keep_latest:]:
            stale_path.unlink(missing_ok=True)

    def _event(self, message: str) -> None:
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.state.setdefault("events", []).append(message)
        self.state["events"] = self.state["events"][-20:]
        print(f"[PrometheusBridge] {message}")

    def _write_bridge(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        state_json = json.dumps(self.state, ensure_ascii=False, indent=2)
        self._atomic_write(self.state_path, f"window.HAI_AVATAR_STATE = {state_json};\n")
        self._atomic_write(self.state_json_path, state_json)
        html = self._html()
        if not self.html_path.exists() or self.html_path.read_text(encoding="utf-8") != html:
            self._atomic_write(self.html_path, html)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)

    def _html(self) -> str:
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>HAI Prometheus Avatar Bridge</title>
  <script src="https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js"></script>
  <script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/pixi.js@6.5.10/dist/browser/pixi.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/pixi-live2d-display@0.4.0/dist/index.min.js"></script>
  <style>
    :root { color-scheme: dark; font-family: Inter, "Microsoft YaHei", sans-serif; }
    body { margin: 0; min-height: 100vh; background: #101014; color: #f4f4f5; display: grid; grid-template-columns: minmax(420px, 1fr) 380px; }
    #avatar { position: relative; width: 100%; height: 100vh; background: radial-gradient(circle at 50% 36%, #18213d 0, #0b0e1b 48%, #070912 100%); overflow: hidden; transform-origin: 50% 70%; animation: idleFloat 4s ease-in-out infinite; }
    #avatar canvas { display: block; width: 100%; height: 100%; }
    #avatarStatus { position: absolute; left: 16px; top: 16px; max-width: min(620px, calc(100% - 32px)); padding: 10px 12px; border: 1px solid #303038; border-radius: 8px; background: rgba(13,13,17,.86); color: #d4d4d8; font: 12px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; pointer-events: none; }
    #avatarStatus.ok { color: #a7f3d0; }
    #avatarStatus.error { color: #fca5a5; }
    #fallbackAvatar { position: absolute; inset: 0; display: none; place-items: center; }
    #fallbackAvatar .figure { width: min(32vw, 220px); aspect-ratio: 1 / 1.45; border-radius: 45% 45% 38% 38%; background: linear-gradient(180deg, #ffd9c7 0 28%, #6ee7b7 28% 100%); box-shadow: 0 28px 80px rgba(0,212,170,.16); transform-origin: 50% 80%; animation: idleFloat 3s ease-in-out infinite; }
    #fallbackAvatar .face { width: 58%; height: 30%; margin: 18% auto 0; border-radius: 45%; background: #ffe8dc; position: relative; }
    #fallbackAvatar .face::before, #fallbackAvatar .face::after { content: ""; position: absolute; top: 42%; width: 9%; height: 9%; border-radius: 50%; background: #202026; }
    #fallbackAvatar .face::before { left: 31%; }
    #fallbackAvatar .face::after { right: 31%; }
    #avatar.nod { animation: nodMotion 700ms ease-in-out, idleFloat 4s ease-in-out infinite 700ms; }
    #avatar.wave { animation: waveMotion 900ms ease-in-out, idleFloat 4s ease-in-out infinite 900ms; }
    #avatar.head_tilt { animation: tiltMotion 900ms ease-in-out, idleFloat 4s ease-in-out infinite 900ms; }
    #avatar.think, #avatar.explain { animation: explainMotion 900ms ease-in-out, idleFloat 4s ease-in-out infinite 900ms; }
    aside { padding: 20px; border-left: 1px solid #2a2a32; background: #17171d; overflow: auto; }
    h1 { font-size: 20px; margin: 0 0 14px; }
    .row { margin: 12px 0; }
    .label { color: #a1a1aa; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    .value { margin-top: 4px; line-height: 1.5; word-break: break-word; }
    .pill { display: inline-block; padding: 3px 8px; border: 1px solid #3f3f46; border-radius: 999px; margin: 2px; }
    button { border: 0; padding: 10px 14px; border-radius: 8px; background: #00d4aa; color: #07100e; font-weight: 700; cursor: pointer; }
    pre { white-space: pre-wrap; background: #0d0d11; padding: 10px; border-radius: 8px; color: #d4d4d8; }
    html.embed body { display: block; overflow: hidden; }
    html.embed aside { display: none; }
    html.embed #avatarStatus { opacity: 0; transition: opacity .25s ease; }
    html.embed #avatarStatus.error { opacity: 1; }
    @keyframes idleFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
    @keyframes nodMotion { 0%,100% { transform: rotate(0deg); } 35% { transform: rotate(2deg) translateY(10px); } 65% { transform: rotate(-1deg) translateY(-4px); } }
    @keyframes waveMotion { 0%,100% { transform: rotate(0deg); } 25% { transform: rotate(4deg); } 50% { transform: rotate(-4deg); } 75% { transform: rotate(3deg); } }
    @keyframes tiltMotion { 0%,100% { transform: rotate(0deg); } 50% { transform: rotate(-7deg); } }
    @keyframes explainMotion { 0%,100% { transform: translateX(0); } 35% { transform: translateX(10px); } 70% { transform: translateX(-6px); } }
  </style>
  <script>if (new URLSearchParams(location.search).get('embed') === '1') document.documentElement.classList.add('embed');</script>
  <script src="./avatar-state.js"></script>
</head>
<body>
  <div id="avatar">
    <div id="avatarStatus">initializing avatar bridge...</div>
    <div id="fallbackAvatar"><div class="figure"><div class="face"></div></div></div>
  </div>
  <aside>
    <h1>HAI Avatar Bridge</h1>
    <button id="speakBtn">Speak latest reply</button>
    <div class="row"><div class="label">Render Status</div><div id="renderStatus" class="value"></div></div>
    <div class="row"><div class="label">Reply</div><div id="reply" class="value"></div></div>
    <div class="row"><div class="label">Expression</div><div id="expression" class="value"></div></div>
    <div class="row"><div class="label">Gestures</div><div id="gestures" class="value"></div></div>
    <div class="row"><div class="label">Voice / Audio</div><div id="audio" class="value"></div></div>
    <div class="row"><div class="label">Events</div><pre id="events"></pre></div>
  </aside>
  <script>
    let state = window.HAI_AVATAR_STATE || {};
    let lastUpdatedAt = '';
    let app = null;
    let model = null;
    let mouthTimer = null;
    let lipSyncActive = false;
    let lipSyncStartedAt = 0;
    let currentAudio = null;
    let lastPlayedAudioUrl = '';
    let gestureIntensity = .5;
    let gestureState = { type: null, startedAt: 0, duration: 0 };
    let gestureQueue = [];
    let lastGestureSignature = '';
    const paramAliases = {
      angleX: ['ParamAngleX', 'PARAM_ANGLE_X'],
      angleY: ['ParamAngleY', 'PARAM_ANGLE_Y'],
      angleZ: ['ParamAngleZ', 'PARAM_ANGLE_Z'],
      bodyAngleX: ['ParamBodyAngleX', 'PARAM_BODY_ANGLE_X'],
      eyeLOpen: ['ParamEyeLOpen', 'PARAM_EYE_L_OPEN'],
      eyeROpen: ['ParamEyeROpen', 'PARAM_EYE_R_OPEN'],
      eyeLSmile: ['ParamEyeLSmile', 'PARAM_EYE_L_SMILE'],
      eyeRSmile: ['ParamEyeRSmile', 'PARAM_EYE_R_SMILE'],
      browLY: ['ParamBrowLY', 'PARAM_BROW_L_Y'],
      browRY: ['ParamBrowRY', 'PARAM_BROW_R_Y'],
      mouthOpen: ['ParamMouthOpenY', 'PARAM_MOUTH_OPEN_Y', 'ParamA'],
      mouthForm: ['ParamMouthForm', 'PARAM_MOUTH_FORM'],
    };
    const emotionParams = {
      neutral: { eyeLOpen: 1, eyeROpen: 1, mouthForm: 0 },
      happy: { eyeLOpen: .82, eyeROpen: .82, eyeLSmile: 1, eyeRSmile: 1, mouthForm: 1 },
      sad: { eyeLOpen: .62, eyeROpen: .62, browLY: -.5, browRY: -.5, mouthForm: -.3 },
      surprised: { eyeLOpen: 1.25, eyeROpen: 1.25, browLY: .8, browRY: .8, mouthOpen: .7 },
      thinking: { eyeLOpen: .72, eyeROpen: .9, browLY: .25, browRY: -.15, angleX: 12 },
    };

    document.addEventListener('DOMContentLoaded', () => {
      renderState(state);
      initAvatar().catch(showError);
    });

    document.getElementById('speakBtn').onclick = async () => {
      if (!state.reply_text) return;
      setEmotion(state.prometheus_emotion || 'neutral');
      animateGestures(state.gestures || [], true, state.gesture_intensity);
      if (!playStateAudio(true)) speakWithBrowser(state.reply_text);
    };

    async function initAvatar() {
      setStatus('checking Live2D runtimes...');
      if (!window.PIXI) throw new Error('PIXI was not loaded. Check cdn.jsdelivr.net access for pixi.js.');
      if (!window.PIXI.live2d?.Live2DModel) {
        throw new Error('pixi-live2d-display was not loaded. Check cdn.jsdelivr.net access for pixi-live2d-display.');
      }
      if (!window.Live2D && !window.Live2DCubismCore) {
        throw new Error('No Live2D runtime was loaded. Check live2d.min.js or Live2DCubismCore network access.');
      }
      disableModelAudio();

      const container = document.getElementById('avatar');
      setStatus(`loading model: ${state.model_url || '(missing model_url)'}`);
      app = new PIXI.Application({
        width: container.clientWidth,
        height: container.clientHeight,
        backgroundAlpha: 0,
        antialias: true,
        resolution: window.devicePixelRatio || 1,
        autoDensity: true,
      });
      container.insertBefore(app.view, document.getElementById('avatarStatus'));

      model = await PIXI.live2d.Live2DModel.from(state.model_url);
      stripModelMotionSounds(model);
      app.stage.addChild(model);
      fitModel();
      try { model.motion?.('Idle', 0, { loop: true }); } catch (_) {}
      try { model.motion?.('idle', 0, { loop: true }); } catch (_) {}
      app.ticker.add(applyLive2DOverlays, null, PIXI.UPDATE_PRIORITY?.LOW ?? -25);
      setEmotion(state.prometheus_emotion || 'neutral');
      animateGestures(state.gestures || [], true, state.gesture_intensity);
      setStatus(`model loaded: ${Math.round(model.width)}x${Math.round(model.height)}`, 'ok');

      window.addEventListener('resize', () => {
        if (!app) return;
        app.renderer.resize(container.clientWidth, container.clientHeight);
        fitModel();
      });
    }

    function renderState(nextState) {
      document.getElementById('renderStatus').textContent = document.getElementById('avatarStatus').textContent;
      document.getElementById('reply').textContent = nextState.reply_text || '(no reply yet)';
      document.getElementById('expression').textContent = `${nextState.expression} -> ${nextState.prometheus_emotion}`;
      document.getElementById('gestures').innerHTML = (nextState.gestures || []).map(g => `<span class="pill">${g}</span>`).join(' ') || '(none)';
      document.getElementById('audio').textContent = `${nextState.voice_style || 'neutral'} | rate/intensity ${Number(nextState.gesture_intensity || 0).toFixed(2)} | ${nextState.audio_url || '(no audio)'}`;
      document.getElementById('events').textContent = (nextState.events || []).join('\\n');
    }

    function animateGestures(gestures, force = false, intensity = .5) {
      const el = document.getElementById('avatar');
      const sequence = gestures.filter(g => g && g !== 'idle');
      gestureIntensity = Math.max(0, Math.min(1, Number(intensity) || 0));
      const signature = sequence.join('|');
      if (signature && (force || signature !== lastGestureSignature)) {
        lastGestureSignature = signature;
        gestureQueue = sequence.slice();
        startNextGesture();
      }
      sequence.forEach((gesture, index) => {
        setTimeout(() => {
          el.classList.remove('nod', 'wave', 'head_tilt', 'think', 'explain', 'agree', 'small_bow');
          void el.offsetWidth;
          el.classList.add(gesture);
          setTimeout(() => el.classList.remove(gesture), 950);
        }, index * 850);
      });
    }

    function fitModel() {
      if (!app || !model) return;
      const width = app.renderer.width / (window.devicePixelRatio || 1);
      const height = app.renderer.height / (window.devicePixelRatio || 1);
      const scale = Math.min(width / model.width, height / model.height) * 0.86;
      model.scale.set(scale);
      if (model.anchor) {
        model.anchor.set(0.5, 0.5);
        model.x = width / 2;
        model.y = height / 2;
      } else {
        model.x = (width - model.width) / 2;
        model.y = (height - model.height) / 2;
      }
    }

    function setEmotion(emotion) {
      if (!model) return;
      const params = emotionParams[emotion] || emotionParams.neutral;
      Object.entries(params).forEach(([name, value]) => setParamAny(paramAliases[name] || [name], value));
    }

    function setParamAny(ids, value) {
      let applied = false;
      ids.forEach((id) => {
        if (setParam(id, value)) applied = true;
      });
      return applied;
    }

    function setParam(id, value) {
      const core = model?.internalModel?.coreModel;
      if (!core) return;
      try {
        if (typeof core.getParameterIndex === 'function' && core.getParameterIndex(id) >= 0) {
          core.setParameterValueById(id, value);
          return true;
        }
      } catch (_) {}
      try {
        if (typeof core.setParameterValueById === 'function') {
          core.setParameterValueById(id, value);
          return true;
        }
      } catch (_) {}
      try {
        if (typeof core.setParamFloat === 'function') {
          core.setParamFloat(id, value);
          return true;
        }
      } catch (_) {}
      return false;
    }

    function speakWithBrowser(text) {
      window.speechSynthesis?.cancel();
      startTextLipSync();
      const fallbackDurationMs = Math.min(7000, Math.max(1200, text.length * 170));
      if ('SpeechSynthesisUtterance' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'zh-CN';
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.onend = stopTextLipSync;
        utterance.onerror = stopTextLipSync;
        window.speechSynthesis.speak(utterance);
        setTimeout(() => {
          if (lipSyncActive && !window.speechSynthesis?.speaking) stopTextLipSync();
        }, fallbackDurationMs);
      } else {
        setTimeout(stopTextLipSync, fallbackDurationMs);
      }
    }

    function playStateAudio(force = false) {
      if (!state.audio_url) return false;
      if (!force && state.audio_url === lastPlayedAudioUrl) return true;
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }
      lastPlayedAudioUrl = state.audio_url;
      currentAudio = new Audio(`${state.audio_url}?turn=${encodeURIComponent(state.turn_id || '')}`);
      currentAudio.onplay = startTextLipSync;
      currentAudio.onended = stopTextLipSync;
      currentAudio.onerror = stopTextLipSync;
      currentAudio.play().catch((error) => {
        stopTextLipSync();
        setStatus(`audio autoplay blocked; use Speak latest reply (${error?.message || error})`, 'error');
      });
      return true;
    }

    function stopStateAudio() {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
      }
      lastPlayedAudioUrl = '';
      stopTextLipSync();
    }

    function startTextLipSync() {
      stopTextLipSync();
      lipSyncActive = true;
      lipSyncStartedAt = performance.now();
      mouthTimer = setInterval(() => {
        if (!lipSyncActive) return;
        const elapsed = (performance.now() - lipSyncStartedAt) / 1000;
        const value = .18 + Math.abs(Math.sin(elapsed * 14)) * .55 + Math.random() * .12;
        setParamAny(paramAliases.mouthOpen, Math.min(.9, value));
      }, 80);
    }

    function stopTextLipSync() {
      if (mouthTimer) clearInterval(mouthTimer);
      mouthTimer = null;
      lipSyncActive = false;
      setParamAny(paramAliases.mouthOpen, 0);
    }

    function startNextGesture() {
      const next = gestureQueue.shift();
      if (!next) {
        gestureState = { type: null, startedAt: 0, duration: 0 };
        return;
      }
      gestureState = {
        type: next,
        startedAt: performance.now(),
        duration: next === 'wave' ? 1100 : 850,
      };
      playModelMotion(next);
      setTimeout(startNextGesture, gestureState.duration + 120);
    }

    function playModelMotion(gesture) {
      if (!model?.motion) return;
      const motionMap = {
        wave: ['TapBody', 'tap_body', 'pinch_in'],
        nod: ['TapBody', 'flick_head', 'tap_body'],
        agree: ['TapBody', 'flick_head', 'tap_body'],
        small_bow: ['TapBody', 'tap_body'],
        head_tilt: ['TapBody', 'flick_head'],
        think: ['TapBody', 'shake'],
        explain: ['TapBody', 'tap_body'],
      };
      const groups = motionMap[gesture] || [];
      for (const group of groups) {
        try {
          const result = model.motion(group, 0);
          setStatus(`model loaded; motion ${group} for gesture ${gesture}`, 'ok');
          if (result?.catch) result.catch(() => {});
          break;
        } catch (_) {}
      }
    }

    function disableModelAudio() {
      try {
        if (PIXI.live2d?.SoundManager) {
          PIXI.live2d.SoundManager.volume = 0;
        }
      } catch (_) {}
    }

    function stripModelMotionSounds(target) {
      const seen = new Set();
      const visit = (value) => {
        if (!value || typeof value !== 'object' || seen.has(value)) return;
        seen.add(value);
        delete value.Sound;
        delete value.sound;
        Object.values(value).forEach(visit);
      };
      visit(target?.internalModel?.settings);
      visit(target?.internalModel?.settings?.json);
      visit(target?.internalModel?.motions);
    }

    function applyLive2DOverlays() {
      if (!model) return;
      if (lipSyncActive) {
        const elapsed = (performance.now() - lipSyncStartedAt) / 1000;
        const mouth = .16 + Math.abs(Math.sin(elapsed * 13.5)) * .62;
        setParamAny(paramAliases.mouthOpen, mouth);
      }
      if (!gestureState.type) return;

      const elapsed = performance.now() - gestureState.startedAt;
      const progress = Math.min(1, elapsed / gestureState.duration);
      const pulse = Math.sin(progress * Math.PI);
      const shake = Math.sin(progress * Math.PI * 5) * pulse;
      const type = gestureState.type;
      const strength = .35 + gestureIntensity * .9;

      if (type === 'nod' || type === 'agree' || type === 'small_bow') {
        setParamAny(paramAliases.angleY, -18 * pulse * strength);
        setParamAny(paramAliases.angleZ, 3 * shake * strength);
      } else if (type === 'wave') {
        setParamAny(paramAliases.angleZ, 12 * shake * strength);
        setParamAny(paramAliases.bodyAngleX, 8 * shake * strength);
        setParamAny(paramAliases.angleX, 10 * shake * strength);
      } else if (type === 'head_tilt' || type === 'think' || type === 'explain') {
        setParamAny(paramAliases.angleZ, -14 * pulse * strength);
        setParamAny(paramAliases.angleX, 8 * pulse * strength);
      }

      if (progress >= 1) {
        gestureState = { type: null, startedAt: 0, duration: 0 };
        setParamAny(paramAliases.angleX, 0);
        setParamAny(paramAliases.angleY, 0);
        setParamAny(paramAliases.angleZ, 0);
        setParamAny(paramAliases.bodyAngleX, 0);
      }
    }

    function setStatus(message, kind = '') {
      const status = document.getElementById('avatarStatus');
      status.textContent = message;
      status.className = kind;
      document.getElementById('renderStatus').textContent = message;
    }

    function showError(error) {
      console.error(error);
      setStatus(`Live2D avatar failed. ${error?.message || error}`, 'error');
      document.getElementById('fallbackAvatar').style.display = 'grid';
    }

    async function refreshState() {
      try {
        const response = await fetch(`./avatar-state.json?t=${Date.now()}`, { cache: 'no-store' });
        const nextState = await response.json();
        if (nextState.updated_at && nextState.updated_at !== lastUpdatedAt) {
          state = nextState;
          lastUpdatedAt = nextState.updated_at;
          renderState(state);
          setEmotion(state.prometheus_emotion || 'neutral');
          animateGestures(state.gestures || [], true, state.gesture_intensity);
          if (state.speaking && state.audio_url) {
            playStateAudio();
          } else if (!state.audio_url && currentAudio) {
            stopStateAudio();
          } else if (!state.speaking && currentAudio?.ended) {
            stopTextLipSync();
          }
        }
      } catch (error) {
        console.warn('Failed to refresh avatar state', error);
      }
    }

    setInterval(refreshState, 250);
  </script>
</body>
</html>
"""
