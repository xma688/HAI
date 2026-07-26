"""MOSS-TTS-Nano ONNX provider for local text-to-speech."""

import asyncio
import logging
import wave
from pathlib import Path

from hai_avatar.schemas import TTSResult
from hai_avatar.tts.base import TTSProvider

logger = logging.getLogger(__name__)


class MossTTSProvider(TTSProvider):
    def __init__(
        self,
        repo_path: str | Path = "third_party/models/MOSS-TTS-Nano",
        prompt_audio: str | Path = "data/voice_prompts/default.wav",
        model_dir: str | Path = "third_party/models/MOSS-TTS-Nano/models/MOSS-TTS-Nano-100M-ONNX",
        backend: str = "onnx",
    ) -> None:
        from hai_avatar.config import PROJECT_ROOT

        self._project_root = PROJECT_ROOT
        self._repo_path = self._project_root / repo_path
        self._prompt_audio = self._project_root / prompt_audio
        self._model_dir = self._project_root / model_dir
        self._backend = backend

        if not self._repo_path.exists():
            raise FileNotFoundError(f"MOSS repo not found: {self._repo_path}")
        if not self._prompt_audio.exists():
            raise FileNotFoundError(f"Prompt audio not found: {self._prompt_audio}")
        if not self._model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {self._model_dir}")

        logger.info("MOSS TTS initialized")
        logger.info("  repo: %s", self._repo_path)
        logger.info("  prompt_audio: %s", self._prompt_audio)
        logger.info("  model_dir: %s", self._model_dir)

    async def synthesize(self, text: str, voice_style: str, output_path: Path) -> TTSResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        await self._run_cli(text, output_path)

        duration_ms = self._get_duration_ms(output_path)
        logger.info("MOSS TTS saved to %s (%.2f s)", output_path, duration_ms / 1000)

        return TTSResult(
            audio_path=str(output_path),
            duration_ms=duration_ms,
            sample_rate=16000,
        )

    async def _run_cli(self, text: str, output_path: Path) -> None:
        output_path = output_path.resolve()

        cmd = [
            "moss-tts-nano",
            "generate",
            "--backend", self._backend,
            "--prompt-speech", str(self._prompt_audio),
            "--text", text,
            "--output", str(output_path),
            "--mode", "voice_clone",
            "--onnx-model-dir", str(self._model_dir.parent),  # 指向父目录
        ]

        # logger.info("Running MOSS CLI: %s", " ".join(cmd))
        logger.info("=" * 60)
        logger.info("Running MOSS CLI:")
        logger.info("  Command: %s", " ".join(cmd))
        logger.info("  CWD: %s", self._repo_path)
        logger.info("  Output: %s", output_path)
        logger.info("=" * 60)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self._repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace") if stderr else "Unknown error"
                raise RuntimeError(f"MOSS TTS failed (code {process.returncode}): {error_msg}")

        except FileNotFoundError:
            raise RuntimeError(
                "moss-tts-nano command not found. "
                f"Please ensure MOSS repo is installed with 'pip install -e .' in {self._repo_path}"
            )
        except Exception as e:
            raise RuntimeError(f"MOSS TTS synthesis failed: {e}")

        if not output_path.exists():
            raise FileNotFoundError(f"Output file not generated: {output_path}")

    @staticmethod
    def _get_duration_ms(audio_path: Path) -> int:
        try:
            with wave.open(str(audio_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return int(frames / rate * 1000) if rate else 0
        except (wave.Error, EOFError, FileNotFoundError):
            return 0