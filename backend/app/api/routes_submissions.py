from pathlib import Path, PurePath
from tempfile import TemporaryDirectory
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis_result import AnalysisResult
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
from app.services.audio_extract_service import AudioExtractionError, extract_audio
from app.services.feedback_service import FeedbackGenerationError, generate_feedback
from app.services.filler_word_service import detect_filler_words
from app.services.media_probe_service import InvalidMediaError, probe_media
from app.services.minio_service import minio_service
from app.services.silence_service import SilenceDetectionError, detect_silence
from app.services.speech_metrics_service import (
    calculate_pace_segments,
    calculate_speech_rate,
)
from app.services.stt_service import TranscriptionError, transcribe_audio
from app.services.transcript_cleanup_service import (
    TranscriptCleanupError,
    clean_transcript,
)
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

        suffix = PurePath(block.media_object_key).suffix.lower() or ".media"
        with TemporaryDirectory(prefix="haca-analysis-") as temp_dir:
            media_path = Path(temp_dir) / f"input{suffix}"
            audio_path = Path(temp_dir) / "audio.mp3"
            try:
                minio_service.download_object(
                    minio_service.bucket,
                    block.media_object_key,
                    media_path,
                )
                media_info = probe_media(str(media_path))
                media_info["object_key"] = block.media_object_key
                media_info["format"]["filename"] = PurePath(block.media_object_key).name
                extract_audio(str(media_path), str(audio_path))
                silence_result = detect_silence(str(audio_path))
                stt_result = transcribe_audio(str(audio_path))
            except (BotoCoreError, ClientError) as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"uploaded media could not be downloaded: {exc}",
                ) from exc
            except InvalidMediaError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid media file: {exc}",
                ) from exc
            except AudioExtractionError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"audio extraction failed: {exc}",
                ) from exc
            except SilenceDetectionError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"silence detection failed: {exc}",
                ) from exc
            except TranscriptionError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenAI STT failed: {exc}",
                ) from exc

        transcript = stt_result["text"]
        filler_result = detect_filler_words(transcript)
        speech_result = calculate_speech_rate(
            transcript, silence_result["speech_duration_seconds"]
        )
        pace_result = calculate_pace_segments(
            words=stt_result.get("words", []),
            transcript_segments=stt_result.get("segments", []),
            baseline_rate=speech_result["speech_rate_eojeol_per_minute"],
        )
        metrics = AnalysisMetrics(
            speech_rate_eojeol_per_minute=speech_result[
                "speech_rate_eojeol_per_minute"
            ],
            filler_word_count=filler_result["filler_word_count"],
            silence_count=silence_result["silence_count"],
            silence_total_seconds=silence_result["silence_total_seconds"],
        )
        metrics_payload = {
            **metrics.model_dump(),
            "speech": speech_result,
            "pace": pace_result,
            "filler_words": filler_result,
            "silence": silence_result,
            "stt": {
                "provider": stt_result.get("provider"),
                "model": stt_result.get("model"),
                "segment_count": len(stt_result.get("segments", [])),
                "word_count": len(stt_result.get("words", [])),
                "segments": stt_result.get("segments", []),
                "words": stt_result.get("words", []),
            },
        }
        try:
            cleanup_result = clean_transcript(
                transcript,
                question=block.question,
                resume=payload.resume,
            )
        except TranscriptCleanupError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI transcript cleanup failed: {exc}",
            ) from exc

        cleaned_text = cleanup_result["text"]
        metrics_payload["transcript_cleanup"] = {
            "model": cleanup_result.get("model"),
            "corrections": cleanup_result.get("corrections", []),
        }
        try:
            feedback = generate_feedback(
                metrics_payload,
                cleaned_text,
                question=block.question,
                resume=payload.resume,
            )
        except FeedbackGenerationError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI feedback generation failed: {exc}",
            ) from exc

        media_info_key = minio_service.build_analysis_object_key(
            payload.virtual_user_id, submission_id, block.block_id, "media_info.json"
        )
        stt_key = minio_service.build_analysis_object_key(
            payload.virtual_user_id, submission_id, block.block_id, "stt.txt"
        )
        cleaned_script_key = minio_service.build_analysis_object_key(
            payload.virtual_user_id, submission_id, block.block_id, "cleaned_script.txt"
        )
        metrics_key = minio_service.build_analysis_object_key(
            payload.virtual_user_id, submission_id, block.block_id, "metrics.json"
        )
        feedback_key = minio_service.build_analysis_object_key(
            payload.virtual_user_id, submission_id, block.block_id, "feedback.txt"
        )

        minio_service.put_json(media_info_key, media_info)
        minio_service.put_text(stt_key, transcript)
        minio_service.put_text(cleaned_script_key, cleaned_text)
        minio_service.put_json(metrics_key, metrics_payload)
        minio_service.put_text(feedback_key, feedback["feedback"])

        analysis_result = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.block_id == block_uuid)
            .order_by(AnalysisResult.created_at.desc())
            .first()
        )
        if analysis_result is None:
            analysis_result = AnalysisResult(id=new_uuid(), block_id=block_uuid)
            db.add(analysis_result)
        analysis_result.media_info_object_key = media_info_key
        analysis_result.stt_object_key = stt_key
        analysis_result.cleaned_script_object_key = cleaned_script_key
        analysis_result.metrics_object_key = metrics_key
        analysis_result.feedback_object_key = feedback_key
        analysis_result.speech_rate_eojeol_per_minute = metrics.speech_rate_eojeol_per_minute
        analysis_result.filler_word_count = metrics.filler_word_count
        analysis_result.silence_count = metrics.silence_count
        analysis_result.gaze_off_count = metrics.gaze_off_count
        submission_block.media_type = "video"
        submission_block.status = "analyzed"

        results.append(
            BlockAnalysisResult(
                block_id=block.block_id,
                media_type="video",
                metrics=metrics,
                original_text=transcript,
                cleaned_text=cleaned_text,
                feedback=feedback["feedback"],
            )
        )

    submission.status = "completed"
    db.commit()
    return AnalyzeSubmissionResponse(
        submission_id=submission_id,
        status=submission.status,
        results=results,
    )
