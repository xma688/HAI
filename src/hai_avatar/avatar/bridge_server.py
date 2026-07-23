"""Small local HTTP server for the Prometheus browser bridge."""

from __future__ import annotations

import io
import json
import logging
import threading
import time
import wave
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

logger = logging.getLogger(__name__)


def _silent_wav_bytes(duration_ms: int = 50, sample_rate: int = 16_000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frame_count = max(1, int(sample_rate * duration_ms / 1000))
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


_SILENT_WAV = _silent_wav_bytes()


class _AudioPlaybackGate:
    """Allow one real bridge audio response for each generated turn."""

    def __init__(self, claim_ttl_seconds: float = 600.0) -> None:
        self._claim_ttl_seconds = claim_ttl_seconds
        self._claims: dict[str, float] = {}
        self._served = 0
        self._suppressed = 0
        self._lock = threading.Lock()

    def claim(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            expired = [
                claim_key
                for claim_key, claimed_at in self._claims.items()
                if now - claimed_at >= self._claim_ttl_seconds
            ]
            for claim_key in expired:
                self._claims.pop(claim_key, None)
            if key in self._claims:
                self._suppressed += 1
                return False
            self._claims[key] = now
            self._served += 1
            return True

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "real_audio_responses": self._served,
                "suppressed_duplicate_responses": self._suppressed,
                "active_claims": len(self._claims),
            }


class _QuietStaticHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, audio_gate: _AudioPlaybackGate, **kwargs) -> None:
        self.audio_gate = audio_gate
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args) -> None:
        logger.debug("Avatar bridge: " + format, *args)

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/audio-claim-status.json":
            self._serve_claim_status()
            return
        if parsed.path.startswith("/audio/"):
            self._serve_claimed_audio(parsed.path, parsed.query)
            return
        super().do_GET()

    def _serve_claim_status(self) -> None:
        payload = json.dumps(self.audio_gate.snapshot()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_claimed_audio(self, request_path: str, query: str) -> None:
        filename = Path(unquote(request_path)).name
        audio_path = Path(self.directory).resolve() / "audio" / filename
        if not filename or not audio_path.is_file():
            self.send_error(404, "Audio file not found")
            return

        params = parse_qs(query)
        is_manual_replay = params.get("manual", [""])[0] == "1"
        turn_id = params.get("turn", [""])[0][:128]
        claim_key = f"{turn_id or 'no-turn'}:{filename}"
        should_serve_real_audio = is_manual_replay or self.audio_gate.claim(claim_key)
        if should_serve_real_audio:
            payload = audio_path.read_bytes()
            content_type = "audio/wav" if audio_path.suffix.lower() == ".wav" else "application/octet-stream"
            claim_status = "manual" if is_manual_replay else "served"
        else:
            payload = _SILENT_WAV
            content_type = "audio/wav"
            claim_status = "suppressed"
            logger.info("Suppressed duplicate avatar audio request for turn %s", turn_id or "unknown")

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "none")
        self.send_header("X-HAI-Audio-Claim", claim_status)
        self.end_headers()
        self.wfile.write(payload)


def start_avatar_bridge_server(
    directory: Path,
    host: str = "127.0.0.1",
    port: int = 7861,
) -> ThreadingHTTPServer:
    """Start a daemonized static server and return its handle."""

    directory.mkdir(parents=True, exist_ok=True)
    audio_gate = _AudioPlaybackGate()
    handler = partial(_QuietStaticHandler, directory=str(directory), audio_gate=audio_gate)
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(
        target=server.serve_forever,
        name="hai-avatar-bridge",
        daemon=True,
    )
    thread.start()
    logger.info("Avatar bridge available at http://%s:%s", host, port)
    return server
