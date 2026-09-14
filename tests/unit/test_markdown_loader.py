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


def test_load_extracts_paragraph_blocks(fixture_path: Path):
    doc = MarkdownLoader().load(fixture_path)
    paragraphs = [b for b in doc.blocks if b.kind == "paragraph"]
    texts = [b.text for b in paragraphs]
    assert any("介绍段落" in t for t in texts)
    assert any("普通段落" in t for t in texts)


def test_plain_text_note_yields_paragraph_block(tmp_path: Path):
    note = tmp_path / "note.md"
    note.write_text("一、需求要点A\r\n二、需求要点B\r\n", encoding="utf-8", newline="")
    doc = MarkdownLoader().load(note)
    paragraphs = [b for b in doc.blocks if b.kind == "paragraph"]
    assert paragraphs
    assert "需求要点A" in paragraphs[0].text
    assert "需求要点B" in paragraphs[0].text


@pytest.fixture
def fixture_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample.md"
