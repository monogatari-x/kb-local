from pathlib import Path

import pytest

from kb_core.loaders.text_loader import TextLoader


def test_supported_extensions():
    assert {".txt", ".log", ".csv", ".tsv"} == TextLoader().supported_extensions()


def test_load_returns_blocks_per_paragraph(fixture_path: Path):
    doc = TextLoader().load(fixture_path)
    assert doc.language is None
    assert "第一段" in doc.text
    assert len(doc.blocks) >= 2
    assert doc.blocks[0].start_line == 1
    assert doc.blocks[0].kind == "paragraph"


def test_load_empty_file(tmp_path: Path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    doc = TextLoader().load(p)
    assert doc.text == ""
    assert doc.blocks == []


@pytest.fixture
def fixture_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample.txt"
