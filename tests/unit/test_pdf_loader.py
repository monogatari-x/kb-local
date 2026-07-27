from pathlib import Path


def _make_pdf(path: Path, pages: list[str]) -> Path:
    from fpdf import FPDF

    pdf = FPDF()
    for body in pages:
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        pdf.multi_cell(0, 10, body)
    pdf.output(path)
    return path


def test_pdf_loader_supported_extensions():
    from kb_core.loaders.pdf_loader import PDFLoader

    assert ".pdf" in PDFLoader().supported_extensions()


def test_pdf_loader_extracts_text(tmp_path: Path):
    from kb_core.loaders.pdf_loader import PDFLoader

    pdf_path = _make_pdf(tmp_path / "sample.pdf", ["Hello PDF world"])
    result = PDFLoader().load(pdf_path)
    assert "Hello PDF world" in result.text
    assert len(result.blocks) >= 1


def test_pdf_loader_multi_page(tmp_path: Path):
    from kb_core.loaders.pdf_loader import PDFLoader

    pdf_path = _make_pdf(
        tmp_path / "multi.pdf",
        ["Page one content", "Page two content"],
    )
    result = PDFLoader().load(pdf_path)
    assert "Page one content" in result.text
    assert "Page two content" in result.text
    assert len(result.blocks) == 2


def test_pdf_loader_missing_file(tmp_path: Path):
    import pytest

    from kb_core.exceptions import FilePathError
    from kb_core.loaders.pdf_loader import PDFLoader

    with pytest.raises(FilePathError):
        PDFLoader().load(tmp_path / "nonexistent.pdf")
