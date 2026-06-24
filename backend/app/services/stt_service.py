from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import OpenAI, OpenAIError

from app.core.config import settings


class TranscriptNotFoundError(Exception):
    pass


class TranscriptionError(Exception):
    pass


def load_sample_transcript() -> str:
    transcript_path = Path(settings.stt_sample_transcript_path)
    if not transcript_path.exists():
        raise TranscriptNotFoundError(
            f"sample STT transcript not found: {transcript_path}"
        )
    return transcript_path.read_text(encoding="utf-8").strip()


def _as_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return {
        key: getattr(item, key)
        for key in ("id", "seek", "start", "end", "text", "word")
        if hasattr(item, key)
    }


def _normalize_segments(items: Any) -> list[dict[str, Any]]:
    normalized = []
    for item in items or []:
        data = _as_dict(item)
        normalized.append(
            {
                "id": data.get("id"),
                "start": data.get("start"),
                "end": data.get("end"),
                "text": (data.get("text") or "").strip(),
            }
        )
    return normalized


def _normalize_words(items: Any) -> list[dict[str, Any]]:
    normalized = []
    for item in items or []:
        data = _as_dict(item)
        word = data.get("word") or data.get("text") or ""
        normalized.append(
            {
                "word": str(word).strip(),
                "start": data.get("start"),
                "end": data.get("end"),
            }
        )
    return [item for item in normalized if item["word"]]


def transcribe_audio(audio_path: str) -> dict[str, Any]:
    provider = settings.stt_provider.lower().strip()
    if provider == "sample":
        return {"text": load_sample_transcript(), "provider": "sample", "segments": [], "words": []}
    if provider != "whisper":
        raise TranscriptionError(f"unsupported STT provider: {settings.stt_provider}")
    if not settings.openai_api_key:
        raise TranscriptionError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=settings.openai_stt_model,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment", "word"],
                language="ko",
            )
    except OpenAIError as exc:
        raise TranscriptionError(str(exc)) from exc

    if isinstance(transcription, str):
        text = transcription
        segments = []
        words = []
    else:
        text = getattr(transcription, "text", "") or ""
        segments = _normalize_segments(getattr(transcription, "segments", []))
        words = _normalize_words(getattr(transcription, "words", []))

    return {
        "text": text.strip(),
        "provider": provider,
        "model": settings.openai_stt_model,
        "segments": segments,
        "words": words,
    }
