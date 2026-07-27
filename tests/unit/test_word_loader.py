from pathlib import Path

import pytest

from kb_core.exceptions import FilePathError
from kb_core.loaders.word_loader import WordLoader


def _make_docx(path: Path, paragraphs: list[str]) -> Path:
    from docx import Document

    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(path)
    return path


def test_word_loader_supported_extensions():
    assert ".docx" in WordLoader().supported_extensions()


def test_word_loader_extracts_paragraphs(tmp_path: Path):
    path = _make_docx(tmp_path / "sample.docx", ["First paragraph", "Second paragraph"])
    result = WordLoader().load(path)
    assert "First paragraph" in result.text
    assert "Second paragraph" in result.text
    assert len(result.blocks) == 2


def test_word_loader_skips_empty_paragraphs(tmp_path: Path):
    path = _make_docx(tmp_path / "doc.docx", ["Content", "", "More content"])
    result = WordLoader().load(path)
    assert len(result.blocks) == 2


def test_word_loader_missing_file(tmp_path: Path):
    with pytest.raises(FilePathError):
        WordLoader().load(tmp_path / "nonexistent.docx")
