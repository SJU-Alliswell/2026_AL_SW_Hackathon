from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    virtual_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("virtual_users.id"), nullable=False
    )
    resume_object_key: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="created", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    virtual_user = relationship("VirtualUser", back_populates="submissions")
    blocks = relationship(
        "SubmissionBlock", back_populates="submission", cascade="all, delete-orphan"
    )
