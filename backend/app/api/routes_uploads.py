from fastapi import APIRouter

from app.schemas.upload import (
    MultipartCompleteRequest,
    MultipartCompleteResponse,
    MultipartInitiateRequest,
    MultipartInitiateResponse,
)
from app.services.minio_service import minio_service

router = APIRouter()


@router.post("/uploads/multipart/initiate", response_model=MultipartInitiateResponse)
def initiate_multipart_upload(
    payload: MultipartInitiateRequest,
) -> MultipartInitiateResponse:
    object_key = minio_service.build_raw_object_key(
        virtual_user_id=payload.virtual_user_id,
        submission_id=payload.submission_id,
        block_id=payload.block_id,
        filename=payload.filename,
    )
    upload = minio_service.initiate_multipart_upload(
        object_key=object_key,
        file_size=payload.file_size,
        content_type=payload.content_type,
    )
    return MultipartInitiateResponse(**upload)


@router.post("/uploads/multipart/complete", response_model=MultipartCompleteResponse)
def complete_multipart_upload(
    payload: MultipartCompleteRequest,
) -> MultipartCompleteResponse:
    minio_service.complete_multipart_upload(
        bucket=payload.bucket,
        object_key=payload.object_key,
        upload_id=payload.upload_id,
        parts=[part.model_dump() for part in payload.parts],
    )
    return MultipartCompleteResponse(object_key=payload.object_key, completed=True)
