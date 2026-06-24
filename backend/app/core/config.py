from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "local"
    database_url: str = "postgresql+psycopg://haca:haca@localhost:5432/haca"

    minio_endpoint: str = "localhost:9100"
    minio_public_endpoint: str | None = None
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "haca-media"
    minio_secure: bool = False

    openai_api_key: str = ""
    openai_feedback_model: str = "gpt-4.1-mini"
    openai_cleanup_model: str = "gpt-4.1-mini"
    openai_stt_model: str = "whisper-1"
    stt_provider: str = "whisper"
    stt_sample_transcript_path: str = "./samples/sample_stt_transcript.txt"
    work_dir: str = "./tmp"
    max_upload_size_mb: int = 500

    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
