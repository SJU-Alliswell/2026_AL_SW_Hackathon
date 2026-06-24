from pydantic import BaseModel


class AnalysisMetrics(BaseModel):
    speech_rate_eojeol_per_minute: float | None = None
    filler_word_count: int | None = None
    silence_count: int | None = None
    gaze_off_count: int | None = None


class BlockAnalysisResult(BaseModel):
    block_id: str
    media_type: str | None = None
    metrics: AnalysisMetrics
    original_text: str | None = None
    cleaned_text: str | None = None
    feedback: str | None = None


class AnalyzeSubmissionResponse(BaseModel):
    submission_id: str
    status: str
    results: list[BlockAnalysisResult]
