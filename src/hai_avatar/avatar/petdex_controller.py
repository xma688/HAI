"""Petdex-style browser bridge controller.

This backend writes a lightweight local page that renders a Petdex pet asset
and maps HAI gesture labels onto Petdex-style display states.
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


PETDEX_STATE_MAP = {
    "idle": "idle",
    "nod": "run_right",
    "agree": "jumping",
    "wave": "waving",
    "head_tilt": "run_left",
    "think": "idle",
    "explain": "waving",
    "small_bow": "review",
}


class PetdexAvatarController(AvatarController):
    """Write Petdex-compatible browser bridge state from Python commands."""

    def __init__(self, output_dir: Path, pet_dir: Path) -> None:
        self.output_dir = output_dir
        self.pet_dir = pet_dir
        self.state_path = self.output_dir / "avatar-state.js"
        self.state_json_path = self.output_dir / "avatar-state.json"
        self.html_path = self.output_dir / "index.html"
        self.asset_dir = self.output_dir / "assets"
        self.sprite_url = "./assets/spritesheet.webp"
        self.state: dict[str, Any] = {
            "connected": False,
            "turn_id": None,
            "reply_text": "",
            "expression": "neutral",
            "gestures": [],
            "gesture_intensity": 0.5,
            "petdex_state": "idle",
            "voice_style": "neutral",
            "audio_path": None,
            "audio_url": None,
            "audio_duration_ms": 0,
            "speaking": False,
            "events": [],
            "pet": self._load_pet_manifest(),
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
        logger.info("Petdex bridge ready at %s", self.html_path)

    async def set_reply_text(self, reply_text: str, voice_style: str = "neutral") -> None:
        self._cancel_playback_task()
        self.state["turn_id"] = uuid.uuid4().hex
        self.state["reply_text"] = reply_text
        self.state["voice_style"] = voice_style
        self.state["gestures"] = []
        self.state["gesture_intensity"] = 0.5
        self.state["petdex_state"] = "idle"
        self.state["audio_path"] = None
        self.state["audio_url"] = None
        self.state["audio_duration_ms"] = 0
        self.state["speaking"] = False
        self._reset_after_playback = False
        self._event("reply_text updated")
        self._write_bridge()

    async def set_expression(self, expression: str) -> None:
        self.state["expression"] = expression
        self._event(f"expression -> {expression}")
        self._write_bridge()

    async def trigger_gesture(self, gesture: str, intensity: float = 0.5) -> None:
        self.state.setdefault("gestures", []).append(gesture)
        self.state["gesture_intensity"] = max(0.0, min(1.0, intensity))
        self.state["petdex_state"] = PETDEX_STATE_MAP.get(gesture, "idle")
        self._event(f"gesture -> {gesture}")
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
                name=f"petdex-playback-{turn_id or 'unknown'}",
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
        self.state["gestures"] = []
        self.state["gesture_intensity"] = 0.5
        self.state["petdex_state"] = "idle"
        self.state["speaking"] = False

    async def _finish_playback(self, turn_id: str | None, duration_seconds: float) -> None:
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
        self._cancel_playback_task()
        self.state.update(
            {
                "turn_id": None,
                "reply_text": "",
                "expression": "neutral",
                "gestures": [],
                "gesture_intensity": 0.5,
                "petdex_state": "idle",
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

    def _prepare_assets(self) -> None:
        sprite_name = str(self.state["pet"].get("spritesheetPath", "spritesheet.webp"))
        sprite_path = self.pet_dir / sprite_name
        if not sprite_path.exists():
            return
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        destination = self.asset_dir / "spritesheet.webp"
        if not destination.exists() or sprite_path.stat().st_mtime_ns != destination.stat().st_mtime_ns:
            shutil.copy2(sprite_path, destination)
        self.sprite_url = f"./assets/{destination.name}"

    def _load_pet_manifest(self) -> dict[str, Any]:
        manifest_path = self.pet_dir / "pet.json"
        default_manifest = {
            "id": "eve",
            "displayName": "EVE",
            "description": "",
            "spritesheetPath": "spritesheet.webp",
        }
        if not manifest_path.exists():
            return default_manifest
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Invalid Petdex manifest at %s; using defaults", manifest_path)
            return default_manifest
        return {**default_manifest, **manifest}

    def _event(self, message: str) -> None:
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.state.setdefault("events", []).append(message)
        self.state["events"] = self.state["events"][-20:]
        print(f"[PetdexBridge] {message}")

    def _write_bridge(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._prepare_assets()
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
      pet_name = self.state["pet"].get("displayName", "Pet")
      sprite_src = self.sprite_url
      return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>HAI Petdex Avatar Bridge</title>
  <script>
    document.documentElement.dataset.embed = new URLSearchParams(location.search).get('embed') === '1' ? '1' : '0';
  </script>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, "Microsoft YaHei", sans-serif; }}
    body {{ margin: 0; min-height: 100vh; background: transparent; color: #f5f7fb; overflow: hidden; }}
    #stage {{ position: relative; min-height: 100vh; display: grid; place-items: center; overflow: hidden; background: transparent; }}
    #petRoot {{ width: min(46vw, 360px); aspect-ratio: 192 / 208; display: grid; place-items: center; transform-origin: 50% 70%; animation: petIdle 3s ease-in-out infinite; }}
    #petFrame {{ width: 192px; height: 208px; overflow: hidden; transform: scale(var(--pet-scale, 1)); transform-origin: center; filter: drop-shadow(0 24px 36px rgba(0, 0, 0, .38)); }}
    #petSprite {{ width: 192px; height: 208px; background-image: url("{sprite_src}"); background-repeat: no-repeat; background-size: 1536px 1872px; background-position: 0 0; image-rendering: auto; }}
    
    body[data-pet-state="run_right"] #petRoot {{ animation: petRun 850ms ease-in-out infinite; }}
    body[data-pet-state="run_left"] #petRoot {{ animation: petRun 850ms ease-in-out infinite; }}
    body[data-pet-state="waving"] #petRoot {{ animation: petWave 900ms ease-in-out; }}
    body[data-pet-state="jumping"] #petRoot {{ animation: petJump 600ms ease-in-out; }}
    body[data-pet-state="failed"] #petSprite {{ filter: grayscale(1) opacity(.65) drop-shadow(0 24px 36px rgba(0, 0, 0, .38)); }}
    body[data-pet-state="waiting"] #petRoot {{ animation: petWait 1500ms ease-in-out infinite; }}
    body[data-pet-state="running"] #petRoot {{ animation: petRun 850ms ease-in-out infinite; }}
    body[data-pet-state="review"] #petRoot {{ animation: petReview 800ms ease-in-out; }}
    
    html[data-embed="1"] body {{ min-height: 100vh; background: transparent; overflow: hidden; }}
    html[data-embed="1"] #stage {{ min-height: 100vh; background: transparent; }}
    html[data-embed="1"] #petRoot {{ width: min(72vw, 380px); }}
    
    @keyframes petIdle {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-8px); }} }}
    @keyframes petRun {{ 0%,100% {{ transform: translateY(0) scaleX(1); }} 50% {{ transform: translateY(-14px) scaleX(.98); }} }}
    @keyframes petWave {{ 0%,100% {{ transform: rotate(0deg); }} 25% {{ transform: rotate(7deg); }} 50% {{ transform: rotate(-7deg); }} 75% {{ transform: rotate(5deg); }} }}
    @keyframes petJump {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-24px) scaleY(.95); }} }}
    @keyframes petWait {{ 0%,100% {{ transform: rotate(0deg); }} 50% {{ transform: rotate(-6deg); }} }}
    @keyframes petReview {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(12px); }} }}
    
    @media (max-width: 760px) {{
      #stage {{ min-height: 100vh; }}
      #petRoot {{ width: min(72vw, 320px); }}
    }}
  </style>
  <script src="./avatar-state.js"></script>
</head>
<body data-pet-state="idle" data-gesture="idle" data-expression="neutral">
  <main id="stage">
    <div id="petRoot" aria-label="{pet_name}"><div id="petFrame"><div id="petSprite"></div></div></div>
  </main>
  <script>
    let state = window.HAI_AVATAR_STATE || {{}};
    let lastStateSignature = '';
    let frameTimer = null;
    let idleTimer = null;
    let currentAudio = null;
    let lastPlayedAudioUrl = '';
    const frameWidth = 192;
    const frameHeight = 208;
    const frameDelayMs = 220;
    
    const rowFrameCounts = [6, 8, 8, 4, 5, 8, 6, 6, 6];
    
    const actionMap = {{
      idle: 'idle',
      nod: 'run_right',
      agree: 'jumping',
      wave: 'waving',
      head_tilt: 'run_left',
      think: 'idle',
      explain: 'waving',
      small_bow: 'review',
      run_right: 'run_right',
      run_left: 'run_left',
      waving: 'waving',
      jumping: 'jumping',
      failed: 'failed',
      waiting: 'waiting',
      running: 'running',
      review: 'review',
    }};
    
    const frameSequences = {{
      idle: rowFrames(0),
      run_right: rowFrames(1),
      run_left: rowFrames(2),
      waving: rowFrames(3),
      jumping: rowFrames(4),
      failed: rowFrames(5),
      waiting: rowFrames(6),
      running: rowFrames(7),
      review: rowFrames(8),
    }};

    document.addEventListener('DOMContentLoaded', () => {{
      fitPetFrame();
      setTimeout(() => {{
        renderState(state);
      }}, 100);
      setInterval(refreshState, 300);
      window.addEventListener('resize', fitPetFrame);
    }});

    
    function renderState(nextState) {{
      const gestures = nextState.gestures || ['idle'];
      const activeGestures = gestures.filter(g => g && g !== 'idle');
      const gesture = activeGestures.length > 0 ? activeGestures[activeGestures.length - 1] : 'idle';
      const petSequence = activeGestures
        .map(g => actionMap[g] || 'idle')
        .filter(item => item && item !== 'idle');
      
      let petState = petSequence.length > 0
        ? petSequence[petSequence.length - 1]
        : (nextState.petdex_state || actionMap[gesture] || 'idle');
      
      if (gesture === 'idle' && petState !== 'idle') {{
        petState = 'idle';
      }}
      
      document.body.dataset.petState = petState;
      document.body.dataset.gesture = gesture;
      document.body.dataset.expression = nextState.expression || 'neutral';
      document.body.dataset.speaking = nextState.speaking ? '1' : '0';
      
      const sequenceSignature = petSequence.length > 0 ? petSequence.join('>') : 'idle';
      const signature = `${{nextState.turn_id || nextState.updated_at || ''}}|${{sequenceSignature}}`;
      
      if (signature !== lastStateSignature) {{
        lastStateSignature = signature;
        console.log('[Petdex] State changed:', {{ petState, gesture, petSequence, signature }});
        playGestureSequence(petSequence);
      }}
      if (nextState.speaking && nextState.audio_url) {{
        playStateAudio(nextState.audio_url, nextState.turn_id || '');
      }} else if (!nextState.speaking && currentAudio) {{
        stopStateAudio();
      }}
    }}

    function fitPetFrame() {{
      const root = document.getElementById('petRoot');
      const width = Math.max(1, root.clientWidth);
      document.documentElement.style.setProperty('--pet-scale', String(width / frameWidth));
    }}

    function rowFrames(row) {{
      const count = rowFrameCounts[row] || 1;
      return Array.from({{ length: count }}, (_, col) => [row, col]);
    }}

    function showFrame(frame) {{
      const [row, col] = Array.isArray(frame) ? frame : [0, 0];
      const sprite = document.getElementById('petSprite');
      sprite.style.backgroundPosition = `-${{col * frameWidth}}px -${{row * frameHeight}}px`;
    }}

    function playGestureSequence(gestures) {{
      const queue = gestures.filter((item) => item && item !== 'idle');
      clearInterval(frameTimer);
      clearInterval(idleTimer);
      frameTimer = null;
      idleTimer = null;

      if (!queue.length) {{
        playIdle();
        return;
      }}

      const playNext = () => {{
        const next = queue.shift();
        if (!next) {{
          playIdle();
          return;
        }}
        playGesture(next, playNext);
      }};
      playNext();
    }}

    function playGesture(gesture, onComplete = playIdle) {{
      clearInterval(frameTimer);
      clearInterval(idleTimer);
      frameTimer = null;
      idleTimer = null;

      if (!gesture || gesture === 'idle') {{
        playIdle();
        return;
      }}

      const frames = frameSequences[gesture] || frameSequences.idle;
      let index = 0;
      showFrame(frames[index]);
      frameTimer = setInterval(() => {{
        index += 1;
        if (index >= frames.length) {{
          clearInterval(frameTimer);
          frameTimer = null;
          onComplete();
          return;
        }}
        showFrame(frames[index]);
      }}, frameDelayMs);
    }}

    function playIdle() {{
      clearInterval(idleTimer);
      const frames = frameSequences.idle;
      let index = 0;
      showFrame(frames[index]);
      idleTimer = setInterval(() => {{
        index = (index + 1) % frames.length;
        showFrame(frames[index]);
      }}, 360);
    }}

    function playStateAudio(audioUrl, turnId) {{
      if (!audioUrl || audioUrl === lastPlayedAudioUrl) return;
      lastPlayedAudioUrl = audioUrl;
      stopStateAudio(false);
      const audio = new Audio(`${{audioUrl}}?turn=${{encodeURIComponent(turnId)}}`);
      currentAudio = audio;
      audio.onended = () => stopStateAudio(false);
      audio.onerror = () => stopStateAudio(false);
      audio.play().catch((error) => {{
        console.warn('[Petdex] Audio autoplay failed:', error);
        stopStateAudio(false);
      }});
    }}

    function stopStateAudio(forgetLastPlayed = true) {{
      if (currentAudio) {{
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }}
      currentAudio = null;
      if (forgetLastPlayed) lastPlayedAudioUrl = '';
    }}

    async function refreshState() {{
      try {{
        const response = await fetch(`./avatar-state.json?t=${{Date.now()}}`, {{ 
          cache: 'no-store',
          headers: {{ 'Cache-Control': 'no-cache' }}
        }});
        
        if (!response.ok) {{
          console.warn('[Petdex] Failed to fetch state, status:', response.status);
          return;
        }}
        
        const nextState = await response.json();
        
        const hasStateChanged = nextState.updated_at && 
                               nextState.updated_at !== state.updated_at;
        
        const currentGestures = (state.gestures || []).filter(g => g && g !== 'idle').join('|');
        const newGestures = (nextState.gestures || []).filter(g => g && g !== 'idle').join('|');
        const hasGestureChanged = currentGestures !== newGestures;
        
        const hasPetStateChanged = nextState.petdex_state && 
                                  nextState.petdex_state !== state.petdex_state;
        
        if (hasStateChanged || hasGestureChanged || hasPetStateChanged) {{
          state = nextState;
          console.log('[Petdex] State refreshed:', {{
            gestures: newGestures,
            petState: nextState.petdex_state,
            updatedAt: nextState.updated_at
          }});
          renderState(state);
        }}
      }} catch (error) {{
        console.warn('[Petdex] Failed to refresh state:', error);
      }}
    }}
  </script>
</body>
</html>
"""
