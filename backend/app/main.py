from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.api.routes_submissions import router as submissions_router
from app.api.routes_uploads import router as uploads_router
from app.core.config import settings
from app.core.database import Base, engine

app = FastAPI(title="HACA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submissions_router, prefix="/api/v1", tags=["submissions"])
app.include_router(uploads_router, prefix="/api/v1", tags=["uploads"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
