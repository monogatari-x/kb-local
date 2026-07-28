from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class QdrantConfig(BaseModel):
    url: str = "http://localhost:6333"
    collection: str = "kb_chunks"
    quantization: str = "scalar"


class EmbeddingConfig(BaseModel):
    model: str = "BAAI/bge-m3"
    version: str = "bge-m3-v1"
    device: str = "auto"
    batch_size_cuda: int = 4
    batch_size_cpu: int = 16
    cache_enabled: bool = True


class ChunkingConfig(BaseModel):
    code_max_tokens: int = 800
    text_max_tokens: int = 512
    text_overlap_tokens: int = 50
    keep_code_block_intact: bool = True

    @field_validator("text_overlap_tokens")
    @classmethod
    def _positive_overlap(cls, v: int) -> int:
        if v < 0:
            raise ValueError("text_overlap_tokens must be non-negative")
        return v


class WatchDirConfig(BaseModel):
    path: str
    project_name: str
    project_strategy: str = "fixed"
    recursive: bool = True
    file_types: list[str] = Field(default_factory=list)
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)


class SchedulerConfig(BaseModel):
    full_scan_cron: str = "0 3 * * *"
    incremental_on_start: bool = True


class DatabaseConfig(BaseModel):
    sqlite_path: str = "~/.kb/kb_meta.db"


class Settings(BaseSettings):
    server: ServerConfig = Field(default_factory=ServerConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    watch_dirs: list[WatchDirConfig] = Field(default_factory=list)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


def load_settings(path: Path | None = None) -> Settings:
    if path is None:
        env_path = Path.home() / ".kb" / "config.yaml"
        if env_path.exists():
            path = env_path
        else:
            return Settings()
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return Settings(**data)
