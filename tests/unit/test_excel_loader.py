from pathlib import Path

import pytest

from kb_core.exceptions import FilePathError
from kb_core.loaders.excel_loader import ExcelLoader


def _make_xlsx(path: Path, sheets: dict[str, list[list[object]]]) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    first = True
    for name, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet()
        first = False
        ws.title = name
        for row in rows:
            ws.append(row)
    wb.save(path)
    return path


def test_excel_loader_supported_extensions():
    exts = ExcelLoader().supported_extensions()
    assert ".xlsx" in exts
    assert ".xls" in exts


def test_excel_loader_extracts_single_sheet(tmp_path: Path):
    path = _make_xlsx(
        tmp_path / "sample.xlsx",
        {"Sheet1": [["name", "age"], ["alice", 30], ["bob", 25]]},
    )
    result = ExcelLoader().load(path)
    assert "alice" in result.text
    assert "bob" in result.text
    assert len(result.blocks) == 1


def test_excel_loader_multi_sheet(tmp_path: Path):
    path = _make_xlsx(
        tmp_path / "multi.xlsx",
        {
            "Users": [["name"], ["alice"]],
            "Products": [["sku"], ["X1"]],
        },
    )
    result = ExcelLoader().load(path)
    assert "alice" in result.text
    assert "X1" in result.text
    assert len(result.blocks) == 2


def test_excel_loader_missing_file(tmp_path: Path):
    with pytest.raises(FilePathError):
        ExcelLoader().load(tmp_path / "nonexistent.xlsx")
