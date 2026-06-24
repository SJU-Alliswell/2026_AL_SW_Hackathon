from __future__ import annotations

from collections import defaultdict
import re
from typing import Any


def count_eojeol(text: str) -> int:
    return len([token for token in re.split(r"\s+", text.strip()) if token.strip()])


def calculate_speech_rate(text: str, duration_seconds: float | None) -> dict:
    eojeol_count = count_eojeol(text)
    if duration_seconds is None or duration_seconds <= 0:
        speech_rate = None
    else:
        speech_rate = eojeol_count / (duration_seconds / 60)

    return {
        "eojeol_count": eojeol_count,
        "duration_seconds": duration_seconds,
        "speech_rate_eojeol_per_minute": round(speech_rate, 2)
        if speech_rate is not None
        else None,
    }


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _classify_rate(rate: float | None, baseline: float | None) -> str:
    if rate is None or baseline is None or baseline <= 0:
        return "unknown"
    if rate >= baseline * 1.2:
        return "fast"
    if rate <= baseline * 0.8:
        return "slow"
    return "normal"


def _segments_from_words(words: list[dict[str, Any]], window_seconds: float) -> list[dict[str, Any]]:
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for word in words:
        start = _to_float(word.get("start"))
        end = _to_float(word.get("end"))
        if start is None or end is None:
            continue
        bucket = int(start // window_seconds)
        buckets[bucket].append({"word": word.get("word", ""), "start": start, "end": end})

    segments = []
    for bucket, bucket_words in sorted(buckets.items()):
        bucket_words.sort(key=lambda item: item["start"])
        start = bucket_words[0]["start"]
        end = max(item["end"] for item in bucket_words)
        text = " ".join(item["word"] for item in bucket_words).strip()
        segments.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "word_count": len(bucket_words),
            }
        )
    return segments


def _segments_from_transcript_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for segment in segments:
        start = _to_float(segment.get("start"))
        end = _to_float(segment.get("end"))
        text = (segment.get("text") or "").strip()
        if start is None or end is None or not text:
            continue
        normalized.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "word_count": count_eojeol(text),
            }
        )
    return normalized


def calculate_pace_segments(
    *,
    words: list[dict[str, Any]],
    transcript_segments: list[dict[str, Any]],
    baseline_rate: float | None,
    window_seconds: float = 10.0,
) -> dict[str, Any]:
    source = "word_timestamps"
    segments = _segments_from_words(words, window_seconds)
    if not segments:
        source = "segment_timestamps"
        segments = _segments_from_transcript_segments(transcript_segments)

    pace_segments = []
    for segment in segments:
        duration = max(segment["end"] - segment["start"], 0)
        rate = None
        if duration > 0 and segment["word_count"] > 0:
            rate = segment["word_count"] / (duration / 60)
        status = _classify_rate(rate, baseline_rate)
        if segment["word_count"] < 3 or duration < 1:
            status = "short"
        pace_segments.append(
            {
                "start": round(segment["start"], 3),
                "end": round(segment["end"], 3),
                "duration_seconds": round(duration, 3),
                "word_count": segment["word_count"],
                "speech_rate_eojeol_per_minute": round(rate, 2)
                if rate is not None
                else None,
                "pace": status,
                "text": segment["text"],
            }
        )

    return {
        "source": source,
        "window_seconds": window_seconds if source == "word_timestamps" else None,
        "baseline_eojeol_per_minute": baseline_rate,
        "fast_threshold_eojeol_per_minute": round(baseline_rate * 1.2, 2)
        if baseline_rate is not None
        else None,
        "slow_threshold_eojeol_per_minute": round(baseline_rate * 0.8, 2)
        if baseline_rate is not None
        else None,
        "segments": pace_segments,
        "fast_segments": [item for item in pace_segments if item["pace"] == "fast"],
        "slow_segments": [item for item in pace_segments if item["pace"] == "slow"],
    }
