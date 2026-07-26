import concurrent.futures
import urllib.request
from pathlib import Path

from hai_avatar.avatar.bridge_server import start_avatar_bridge_server


def _fetch(url: str) -> tuple[str | None, bytes]:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.headers.get("X-HAI-Audio-Claim"), response.read()


def test_bridge_serves_real_audio_once_per_turn_under_concurrency(tmp_path: Path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    real_audio = b"real-audio-payload"
    (audio_dir / "reply.wav").write_bytes(real_audio)
    server = start_avatar_bridge_server(tmp_path, port=0)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/audio/reply.wav?turn=same-turn"

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(_fetch, [url] * 8))

        statuses = [status for status, _ in results]
        payloads = [payload for _, payload in results]
        assert statuses.count("served") == 1
        assert statuses.count("suppressed") == 7
        assert payloads.count(real_audio) == 1
        assert all(payload for payload in payloads)

        status, payload = _fetch(f"http://127.0.0.1:{port}/audio/reply.wav?turn=new-turn")
        assert status == "served"
        assert payload == real_audio

        manual_status, manual_payload = _fetch(
            f"http://127.0.0.1:{port}/audio/reply.wav?turn=same-turn&manual=1"
        )
        assert manual_status == "manual"
        assert manual_payload == real_audio
    finally:
        server.shutdown()
        server.server_close()
