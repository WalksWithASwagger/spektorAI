"""WhisperForge CLI — chunked audio transcription to stdout.

Usage:
    python whisperforge.py <audio_file_path> [output_file]

Delegates all chunking + Whisper calls to ``whisperforge_core.audio``. If
``output_file`` is given, writes the combined transcript there; otherwise
prints to stdout.
"""

import sys
from pathlib import Path

from whisperforge_core import audio
from whisperforge_core.logging import get_logger

logger = get_logger(__name__)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python whisperforge.py <audio_file_path> [output_file]", file=sys.stderr)
        return 1

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        return 2

    def _progress(i: int, total: int, label: str) -> None:
        print(f"[{label}] {i}/{total}", file=sys.stderr)

    transcript = audio.transcribe_audio(str(file_path), progress=_progress)

    if len(sys.argv) >= 3:
        output = Path(sys.argv[2])
        output.write_text(transcript, encoding="utf-8")
        print(f"Saved transcript to {output}", file=sys.stderr)
    else:
        print(transcript)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
