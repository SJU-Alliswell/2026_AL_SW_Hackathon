from __future__ import annotations

from openai import OpenAI, OpenAIError

from app.core.config import settings


SYSTEM_PROMPT = """당신은 한국어 면접/발표 코치이자 답변 작성 코치입니다.
지원자의 이력서, 질문, 정제된 STT 답변 텍스트, 기초 분석 결과를 바탕으로 피드백과 개선 답변 예시를 함께 작성하세요.
피드백은 구체적이고 실전적이어야 하며, 사용자가 다음 면접에서 바로 말할 수 있는 자연스러운 답변 문장까지 제공해야 합니다.
발화 속도 분석 결과에 구간별 pace 정보가 있으면 빠르거나 느린 타임스탬프를 근거로 전달력 피드백에 반영하세요.
습관어, 침묵, 발화 속도 같은 전달력 피드백은 정제된 텍스트가 아니라 기초 분석 결과를 우선 근거로 삼으세요.
기초 분석 결과의 transcript_cleanup.corrections는 STT 정제 과정에서 문맥상 보정된 표현입니다. issue_type이 pronunciation_ambiguity이면 수정 전 단어가 틀렸다고 단정하지 말고, 발음상 유사하게 들려 해당 단어가 불명확하게 전달됐을 가능성이 있다고 표현하세요. issue_type이 word_usage이면 발음 문제가 아니라 단어 선택 자체가 문맥과 맞지 않을 수 있다고 피드백하세요.
답변 예시는 STT 내용을 무작정 꾸미지 말고, 이력서와 질문의 맥락 안에서 논리 구조와 표현을 개선한 형태로 작성하세요.
반드시 한국어로 답하고, 칭찬만 하지 말고 개선 행동을 구체적으로 제안하세요.
"""


class FeedbackGenerationError(Exception):
    pass


def generate_feedback(
    metrics: dict,
    transcript: str,
    *,
    question: str,
    resume: str,
) -> dict[str, str]:
    if not settings.openai_api_key:
        raise FeedbackGenerationError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.responses.create(
            model=settings.openai_feedback_model,
            instructions=SYSTEM_PROMPT,
            input=(
                "[이력서]\n"
                f"{resume.strip()}\n\n"
                "[면접/발표 질문]\n"
                f"{question.strip()}\n\n"
                "[정제된 STT 답변 텍스트]\n"
                f"{transcript.strip()}\n\n"
                "[기초 분석 결과]\n"
                f"{metrics}\n\n"
                "아래 형식으로 작성하세요.\n"
                "1. 종합 평가\n"
                "2. 답변 내용 피드백\n"
                "3. 전달력 피드백\n"
                "4. 바로 고칠 행동 3가지\n"
                "5. 사용자가 다음에 말할 답변 예시\n"
                "   - 면접장에서 그대로 말할 수 있는 45~75초 분량의 1인칭 답변으로 작성하세요.\n"
                "   - 문제 상황, 본인 행동, 기술적 판단 근거, 결과, 배운 점이 자연스럽게 이어지게 작성하세요.\n"
                "   - 원문에 없던 경험을 지어내지 말고, 부족한 부분은 과장 없이 보완하세요.\n"
            ),
            max_output_tokens=1100,
        )
    except OpenAIError as exc:
        raise FeedbackGenerationError(str(exc)) from exc

    feedback = getattr(response, "output_text", "").strip()
    if not feedback:
        feedback = str(response)
    return {"feedback": feedback, "model": settings.openai_feedback_model}
