from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "local"
    database_url: str = "postgresql+psycopg://haca:haca@localhost:5432/haca"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "haca-media"
    minio_secure: bool = False

    openai_api_key: str = ""
    stt_provider: str = "whisper"
    work_dir: str = "./tmp"

    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
