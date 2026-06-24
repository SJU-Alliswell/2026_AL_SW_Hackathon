from __future__ import annotations

import re


FILLER_WORDS = [
    "아",
    "음",
    "어",
    "그",
    "저",
    "약간",
    "이제",
    "막",
    "뭐",
    "그러니까",
    "사실",
    "진짜",
]
WORD_BOUNDARY_CHARS = r"가-힣A-Za-z0-9"


def _count_phrase(text: str, phrase: str) -> int:
    pattern = rf"(?<![{WORD_BOUNDARY_CHARS}]){re.escape(phrase)}(?![{WORD_BOUNDARY_CHARS}])"
    return len(re.findall(pattern, text))


def detect_filler_words(text: str) -> dict:
    counts = {word: _count_phrase(text, word) for word in FILLER_WORDS}
    counts = {word: count for word, count in counts.items() if count > 0}
    return {
        "filler_word_count": sum(counts.values()),
        "filler_words": counts,
    }
