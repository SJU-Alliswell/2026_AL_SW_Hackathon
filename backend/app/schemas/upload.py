from pydantic import BaseModel, Field


class MultipartInitiateRequest(BaseModel):
    virtual_user_id: str
    submission_id: str
    block_id: str
    filename: str
    content_type: str | None = None
    file_size: int = Field(gt=0)


class PresignedPart(BaseModel):
    part_number: int
    upload_url: str


class MultipartInitiateResponse(BaseModel):
    bucket: str
    object_key: str
    upload_id: str
    part_size: int
    parts: list[PresignedPart]


class UploadedPart(BaseModel):
    part_number: int
    etag: str


class MultipartCompleteRequest(BaseModel):
    bucket: str
    object_key: str
    upload_id: str
    parts: list[UploadedPart]


class MultipartCompleteResponse(BaseModel):
    object_key: str
    completed: bool
