from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class InvalidMediaError(Exception):
    pass


def probe_media(file_path: str) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise InvalidMediaError("media probe timed out") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or "ffprobe could not parse media"
        raise InvalidMediaError(detail)

    try:
        probe = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InvalidMediaError("ffprobe returned invalid output") from exc

    streams = probe.get("streams") or []
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if not video_streams:
        raise InvalidMediaError("uploaded file has no video stream")
    if not audio_streams:
        raise InvalidMediaError("uploaded file has no audio stream")

    media_streams = [*video_streams, *audio_streams]
    return {
        "filename": Path(file_path).name,
        "format": probe.get("format", {}),
        "streams": [
            {
                "codec_type": stream.get("codec_type"),
                "codec_name": stream.get("codec_name"),
                "duration": stream.get("duration"),
            }
            for stream in media_streams
        ],
    }
