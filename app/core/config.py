import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "IBVAP - Intelligent Border Video Analytics Platform"
    API_V1_STR: str = "/api/v1"
    NODE_TYPE: str = "BOP"  # "BOP" (Border Out Post edge) or "HQ" (Battalion HQ)
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./ibvap_edge.db"

    # Storage Paths
    STORAGE_DIR: str = "./storage"
    SNAPSHOT_DIR: str = "./storage/snapshots"
    CLIP_DIR: str = "./storage/clips"

    # CORS Allowed Origins
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Instantiate settings singleton
settings = Settings()

# Ensure media storage directories exist
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
os.makedirs(settings.CLIP_DIR, exist_ok=True)
