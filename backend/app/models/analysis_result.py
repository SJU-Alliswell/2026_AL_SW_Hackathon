from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    block_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("submission_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_info_object_key: Mapped[str | None] = mapped_column(Text)
    stt_object_key: Mapped[str | None] = mapped_column(Text)
    metrics_object_key: Mapped[str | None] = mapped_column(Text)
    feedback_object_key: Mapped[str | None] = mapped_column(Text)
    cleaned_script_object_key: Mapped[str | None] = mapped_column(Text)
    synthesized_voice_object_key: Mapped[str | None] = mapped_column(Text)
    speech_rate_eojeol_per_minute: Mapped[Decimal | None] = mapped_column(Numeric)
    filler_word_count: Mapped[int | None] = mapped_column(Integer)
    silence_count: Mapped[int | None] = mapped_column(Integer)
    gaze_off_count: Mapped[int | None] = mapped_column(Integer)
    face_detection_ratio: Mapped[Decimal | None] = mapped_column(Numeric)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    block = relationship("SubmissionBlock", back_populates="analysis_result")
