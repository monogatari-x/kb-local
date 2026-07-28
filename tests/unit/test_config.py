from pathlib import Path

import pytest
from pydantic import ValidationError

from kb_core.config import Settings, load_settings


def test_load_from_yaml(fixture_yaml: Path):
    settings = load_settings(fixture_yaml)
    assert settings.qdrant.collection == "kb_chunks"
    assert settings.embedding.model == "BAAI/bge-m3"
    assert settings.embedding.device == "auto"
    assert len(settings.watch_dirs) == 2
    assert settings.watch_dirs[0].project_strategy == "first_subdir"
    assert settings.chunking.text_overlap_tokens == 50


def test_defaults_when_minimal():
    settings = load_settings(None)  # 全用默认值
    assert settings.embedding.batch_size_cpu == 16
    assert settings.chunking.keep_code_block_intact is True
    assert settings.scheduler.incremental_on_start is True


def test_chunking_validation_rejects_negative_overlap():
    with pytest.raises(ValidationError):
        Settings(chunking={"text_overlap_tokens": -5})


@pytest.fixture
def fixture_yaml() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "config_sample.yaml"
