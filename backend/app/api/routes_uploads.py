from pathlib import Path, PurePath
from tempfile import TemporaryDirectory

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.upload import (
    MultipartCompleteRequest,
    MultipartCompleteResponse,
    MultipartInitiateRequest,
    MultipartInitiateResponse,
)
from app.services.media_probe_service import InvalidMediaError, probe_media
from app.services.minio_service import minio_service

router = APIRouter()

ALLOWED_EXTENSIONS = {
    ".avi",
    ".mkv",
    ".mov",
    ".mp4",
    ".webm",
}

ALLOWED_CONTENT_TYPES = {
    "video/avi",
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "video/x-msvideo",
}


def validate_upload_request(payload: MultipartInitiateRequest) -> None:
    extension = PurePath(payload.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        extension_display = extension or "none"
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file extension: {extension_display}",
        )

    content_type = (payload.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        content_type_display = content_type or "none"
        raise HTTPException(
            status_code=400,
            detail=f"unsupported content type: {content_type_display}",
        )

    max_upload_size = settings.max_upload_size_mb * 1024 * 1024
    if payload.file_size > max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=f"file size exceeds {settings.max_upload_size_mb} MB limit",
        )


def validate_completed_media(bucket: str, object_key: str) -> None:
    if bucket != minio_service.bucket:
        raise HTTPException(status_code=400, detail="invalid upload bucket")

    suffix = PurePath(object_key).suffix.lower()
    with TemporaryDirectory(prefix="haca-media-") as temp_dir:
        media_path = Path(temp_dir) / f"upload{suffix}"
        minio_service.download_object(bucket, object_key, media_path)
        probe_media(str(media_path))


@router.post("/uploads/multipart/initiate", response_model=MultipartInitiateResponse)
def initiate_multipart_upload(
    payload: MultipartInitiateRequest,
) -> MultipartInitiateResponse:
    validate_upload_request(payload)

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

    try:
        validate_completed_media(payload.bucket, payload.object_key)
    except InvalidMediaError as exc:
        minio_service.delete_object(payload.bucket, payload.object_key)
        raise HTTPException(
            status_code=400, detail=f"invalid media file: {exc}"
        ) from exc

    return MultipartCompleteResponse(object_key=payload.object_key, completed=True)
