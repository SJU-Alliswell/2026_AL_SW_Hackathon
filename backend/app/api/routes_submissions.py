from pathlib import PurePath
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.submission import Submission
from app.models.submission_block import SubmissionBlock
from app.models.virtual_user import VirtualUser
from app.schemas.result import (
    AnalysisMetrics,
    AnalyzeSubmissionResponse,
    BlockAnalysisResult,
)
from app.schemas.submission import (
    AnalyzeSubmissionRequest,
    SubmissionCreateRequest,
    SubmissionCreateResponse,
    VirtualUserResponse,
)
from app.services.minio_service import minio_service
from app.utils.ids import new_uuid

router = APIRouter()


@router.post("/virtual-users", response_model=VirtualUserResponse)
def create_virtual_user(db: Session = Depends(get_db)) -> VirtualUserResponse:
    virtual_user = VirtualUser(id=new_uuid())
    db.add(virtual_user)
    db.commit()
    return VirtualUserResponse(virtual_user_id=str(virtual_user.id))


@router.post("/submissions", response_model=SubmissionCreateResponse)
def create_submission(
    payload: SubmissionCreateRequest,
    db: Session = Depends(get_db),
) -> SubmissionCreateResponse:
    virtual_user_id = UUID(payload.virtual_user_id)
    virtual_user = db.get(VirtualUser, virtual_user_id)
    if virtual_user is None:
        raise HTTPException(status_code=404, detail="virtual user not found")

    submission = Submission(id=new_uuid(), virtual_user_id=virtual_user_id)
    db.add(submission)
    db.commit()
    return SubmissionCreateResponse(submission_id=str(submission.id))


@router.post(
    "/submissions/{submission_id}/analyze",
    response_model=AnalyzeSubmissionResponse,
)
def analyze_submission(
    submission_id: str,
    payload: AnalyzeSubmissionRequest,
    db: Session = Depends(get_db),
) -> AnalyzeSubmissionResponse:
    submission_uuid = UUID(submission_id)
    virtual_user_id = UUID(payload.virtual_user_id)
    submission = db.get(Submission, submission_uuid)
    if submission is None:
        raise HTTPException(status_code=404, detail="submission not found")
    if submission.virtual_user_id != virtual_user_id:
        raise HTTPException(status_code=400, detail="submission owner mismatch")

    resume_key = minio_service.build_resume_object_key(
        virtual_user_id=payload.virtual_user_id,
        submission_id=submission_id,
    )
    minio_service.put_text(resume_key, payload.resume)
    submission.resume_object_key = resume_key
    submission.status = "analyzing"

    results: list[BlockAnalysisResult] = []
    for block in payload.blocks:
        block_uuid = UUID(block.block_id)
        question_key = minio_service.build_question_object_key(
            virtual_user_id=payload.virtual_user_id,
            submission_id=submission_id,
            block_id=block.block_id,
        )
        minio_service.put_text(question_key, block.question)

        submission_block = db.get(SubmissionBlock, block_uuid)
        if submission_block is None:
            submission_block = SubmissionBlock(
                id=block_uuid,
                submission_id=submission_uuid,
                question_object_key=question_key,
                media_object_key=block.media_object_key,
                original_filename=PurePath(block.media_object_key).name,
                status="uploaded",
            )
            db.add(submission_block)
        else:
            submission_block.question_object_key = question_key
            submission_block.media_object_key = block.media_object_key
            submission_block.status = "uploaded"

        results.append(
            BlockAnalysisResult(
                block_id=block.block_id,
                media_type=None,
                metrics=AnalysisMetrics(),
                original_text=None,
                cleaned_text=None,
                feedback="analysis pipeline is not implemented yet",
            )
        )

    submission.status = "completed"
    db.commit()
    return AnalyzeSubmissionResponse(
        submission_id=submission_id,
        status=submission.status,
        results=results,
    )
