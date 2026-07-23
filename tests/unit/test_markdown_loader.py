from pathlib import Path

import pytest

from kb_core.loaders.markdown_loader import MarkdownLoader


def test_supported_extensions():
    assert {".md", ".markdown"} == MarkdownLoader().supported_extensions()


def test_load_extracts_headings_and_code(fixture_path: Path):
    doc = MarkdownLoader().load(fixture_path)
    kinds = [b.kind for b in doc.blocks]
    assert "heading" in kinds
    assert "code_block" in kinds
    headings = [b for b in doc.blocks if b.kind == "heading"]
    assert headings[0].extra["level"] == 1
    assert headings[0].extra["title"] == "标题 1"


def test_code_block_has_language(fixture_path: Path):
    doc = MarkdownLoader().load(fixture_path)
    code = next(b for b in doc.blocks if b.kind == "code_block")
    assert code.extra["language"] == "python"
    assert "def hello" in code.text


@pytest.fixture
def fixture_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample.md"
