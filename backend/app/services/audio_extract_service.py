from __future__ import annotations

from pathlib import Path
import subprocess


class AudioExtractionError(Exception):
    pass


def extract_audio(input_path: str, output_path: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        output_path,
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise AudioExtractionError("ffmpeg is not installed") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or "ffmpeg audio extraction failed"
        raise AudioExtractionError(detail)
    if not output.exists() or output.stat().st_size == 0:
        raise AudioExtractionError("extracted audio file is empty")
