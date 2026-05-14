from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    data_dir: str = "./data"
    ffmpeg_path: str | None = None
    max_upload_mb: int = 50
    cors_origins: str = "http://localhost:3000"

    @property
    def DATA_DIR(self) -> Path:
        return Path(self.data_dir).resolve()

    @property
    def UPLOADS_DIR(self) -> Path:
        return self.DATA_DIR / "uploads"

    @property
    def JOBS_DIR(self) -> Path:
        return self.DATA_DIR / "jobs"

settings = Settings()

def ensure_dirs() -> None:
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    settings.JOBS_DIR.mkdir(parents=True, exist_ok=True)