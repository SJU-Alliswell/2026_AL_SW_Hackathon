from __future__ import annotations

import json
import re
import subprocess
from typing import Any


class SilenceDetectionError(Exception):
    pass


def _probe_duration(audio_path: str) -> float | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        audio_path,
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
        raise SilenceDetectionError("ffprobe is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise SilenceDetectionError("audio duration probe timed out") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or "ffprobe could not parse audio duration"
        raise SilenceDetectionError(detail)

    try:
        payload = json.loads(result.stdout)
        duration = payload.get("format", {}).get("duration")
        return float(duration) if duration is not None else None
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SilenceDetectionError("ffprobe returned invalid duration output") from exc


def detect_silence(
    audio_path: str,
    *,
    noise_db: int = -35,
    min_duration_seconds: float = 0.7,
) -> dict[str, Any]:
    audio_duration = _probe_duration(audio_path)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        audio_path,
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_duration_seconds}",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise SilenceDetectionError("ffmpeg is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise SilenceDetectionError("silence detection timed out") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or "ffmpeg silence detection failed"
        raise SilenceDetectionError(detail)

    silences: list[dict[str, float]] = []
    current_start: float | None = None
    for line in result.stderr.splitlines():
        start_match = re.search(r"silence_start:\s*([0-9.]+)", line)
        if start_match:
            current_start = float(start_match.group(1))
            continue

        end_match = re.search(
            r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)",
            line,
        )
        if end_match:
            end = float(end_match.group(1))
            duration = float(end_match.group(2))
            start = current_start if current_start is not None else max(end - duration, 0)
            silences.append(
                {
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "duration": round(duration, 3),
                }
            )
            current_start = None

    if current_start is not None and audio_duration is not None and audio_duration > current_start:
        silences.append(
            {
                "start": round(current_start, 3),
                "end": round(audio_duration, 3),
                "duration": round(audio_duration - current_start, 3),
            }
        )

    silence_total = sum(item["duration"] for item in silences)
    speech_duration = None
    if audio_duration is not None:
        speech_duration = max(audio_duration - silence_total, 0)

    return {
        "silence_count": len(silences),
        "silence_total_seconds": round(silence_total, 3),
        "speech_duration_seconds": round(speech_duration, 3)
        if speech_duration is not None
        else None,
        "audio_duration_seconds": round(audio_duration, 3)
        if audio_duration is not None
        else None,
        "silences": silences,
        "params": {
            "noise_db": noise_db,
            "min_duration_seconds": min_duration_seconds,
        },
    }
