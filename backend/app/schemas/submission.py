from pydantic import BaseModel


class VirtualUserResponse(BaseModel):
    virtual_user_id: str


class SubmissionCreateRequest(BaseModel):
    virtual_user_id: str


class SubmissionCreateResponse(BaseModel):
    submission_id: str


class AnalyzeBlockRequest(BaseModel):
    block_id: str
    media_object_key: str
    question: str


class AnalyzeSubmissionRequest(BaseModel):
    virtual_user_id: str
    resume: str
    blocks: list[AnalyzeBlockRequest]
