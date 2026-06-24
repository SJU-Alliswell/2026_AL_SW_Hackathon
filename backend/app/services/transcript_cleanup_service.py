from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from openai import OpenAI, OpenAIError

from app.core.config import settings


SYSTEM_PROMPT = """당신은 한국어 STT 전사문 교정 편집자입니다.
이 작업의 목적은 좋은 답변으로 재작성하는 것이 아니라, 사용자의 발음과 실제 의도한 단어의 차이를 비교할 수 있도록 STT 오인식만 보수적으로 수정하는 것입니다.
면접/발표 질문과 이력서 맥락을 참고하되, 원문 단어와 문장 순서를 최대한 유지하세요.
문맥상 명확하게 잘못 인식된 단어만 가장 가까운 의도 단어로 수정하세요. 예: 기술 용어, 회사명, 프로젝트명, 숫자 표현, 고유명사.
문맥상 확실하지 않은 단어는 추측해서 바꾸지 말고 원문 그대로 두세요.
단어, 구절, 문장을 삭제하거나 요약하지 마세요. 간투사, 반복 표현, 말더듬도 평가 대상이므로 제거하지 마세요.
원문에 없는 경험, 성과, 수치, 기술, 연결 문장을 새로 만들지 마세요.
동의어로 바꾸거나 더 자연스러운 문장으로 풀어쓰지 마세요. 오탈자/오인식 교정에 필요한 최소 변경만 하세요.
출력은 교정된 한국어 답변 본문만 작성하고, 제목/설명/마크다운은 쓰지 마세요.
"""


class TranscriptCleanupError(Exception):
    pass


_TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]+")
_HANGUL_START = ord("가")
_HANGUL_END = ord("힣")
_CHO = (
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
)
_JUNG = (
    "ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅘ",
    "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ", "ㅞ", "ㅟ", "ㅠ", "ㅡ", "ㅢ", "ㅣ",
)
_JONG = (
    "", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ",
    "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
)


def _tokens(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text)


def _token_count(text: str) -> int:
    return len(_tokens(text))


def _decompose_hangul(text: str) -> str:
    parts: list[str] = []
    for char in text:
        code = ord(char)
        if _HANGUL_START <= code <= _HANGUL_END:
            syllable = code - _HANGUL_START
            cho = syllable // 588
            jung = (syllable % 588) // 28
            jong = syllable % 28
            parts.extend((_CHO[cho], _JUNG[jung], _JONG[jong]))
        elif char.strip():
            parts.append(char.lower())
    return "".join(parts)


def _phonetic_similarity(left: str, right: str) -> float:
    left_sound = _decompose_hangul(left.replace(" ", ""))
    right_sound = _decompose_hangul(right.replace(" ", ""))
    if not left_sound or not right_sound:
        return 0.0
    return SequenceMatcher(None, left_sound, right_sound).ratio()


def _classify_correction(stt_text: str, corrected_text: str) -> str:
    if _phonetic_similarity(stt_text, corrected_text) >= 0.58:
        return "pronunciation_ambiguity"
    return "word_usage"


def _feedback_guidance(issue_type: str) -> str:
    if issue_type == "pronunciation_ambiguity":
        return (
            "수정 전 표현이 틀렸다고 단정하지 말고, "
            "발음상 유사하게 들려 해당 단어가 불명확하게 전달됐을 가능성으로만 언급하세요."
        )
    return (
        "발음 유사성보다 문맥상 단어 사용 자체가 어색할 가능성이 큰 항목입니다. "
        "단어 선택이 문맥과 맞지 않을 수 있다고 피드백하세요."
    )


def _extract_corrections(raw_text: str, cleaned_text: str) -> list[dict[str, str | float]]:
    raw_tokens = _tokens(raw_text)
    cleaned_tokens = _tokens(cleaned_text)
    matcher = SequenceMatcher(None, raw_tokens, cleaned_tokens)
    corrections: list[dict[str, str | float]] = []

    for tag, raw_start, raw_end, clean_start, clean_end in matcher.get_opcodes():
        if tag == "equal":
            continue

        stt_text = " ".join(raw_tokens[raw_start:raw_end]).strip()
        corrected_text = " ".join(cleaned_tokens[clean_start:clean_end]).strip()
        if not stt_text or not corrected_text:
            continue

        issue_type = _classify_correction(stt_text, corrected_text)
        corrections.append(
            {
                "stt_text": stt_text,
                "corrected_text": corrected_text,
                "issue_type": issue_type,
                "phonetic_similarity": round(_phonetic_similarity(stt_text, corrected_text), 3),
                "feedback_guidance": _feedback_guidance(issue_type),
            }
        )

    return corrections


def _looks_like_rewrite(raw_text: str, cleaned_text: str) -> bool:
    raw_count = _token_count(raw_text)
    cleaned_count = _token_count(cleaned_text)
    if raw_count == 0 or cleaned_count == 0:
        return cleaned_count == 0 and raw_count > 0

    length_ratio = len(cleaned_text) / max(len(raw_text), 1)
    token_ratio = cleaned_count / raw_count
    similarity = SequenceMatcher(None, raw_text, cleaned_text).ratio()

    if token_ratio < 0.85 or length_ratio < 0.75:
        return True
    return similarity < 0.45 and abs(cleaned_count - raw_count) > max(3, raw_count * 0.2)


def clean_transcript(
    transcript: str,
    *,
    question: str,
    resume: str,
) -> dict[str, Any]:
    raw_text = transcript.strip()
    if not raw_text:
        return {"text": "", "model": settings.openai_cleanup_model, "corrections": []}
    if not settings.openai_api_key:
        raise TranscriptCleanupError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.responses.create(
            model=settings.openai_cleanup_model,
            instructions=SYSTEM_PROMPT,
            input=(
                "[이력서]\n"
                f"{resume.strip()}\n\n"
                "[면접/발표 질문]\n"
                f"{question.strip()}\n\n"
                "[STT 원문]\n"
                f"{raw_text}\n\n"
                "위 STT 원문에서 STT 오인식으로 보이는 오탈자만 최소한으로 수정하세요. "
                "삭제, 요약, 재작성, 동의어 치환은 하지 마세요."
            ),
            max_output_tokens=2000,
        )
    except OpenAIError as exc:
        raise TranscriptCleanupError(str(exc)) from exc

    cleaned_text = getattr(response, "output_text", "").strip()
    if not cleaned_text or _looks_like_rewrite(raw_text, cleaned_text):
        cleaned_text = raw_text

    return {
        "text": cleaned_text,
        "model": settings.openai_cleanup_model,
        "corrections": _extract_corrections(raw_text, cleaned_text),
    }
