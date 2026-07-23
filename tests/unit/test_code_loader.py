from pathlib import Path

import pytest

from kb_core.loaders.code_loader import CodeLoader


def test_supported_extensions_includes_common():
    exts = CodeLoader().supported_extensions()
    assert ".php" in exts
    assert ".py" in exts
    assert ".java" in exts
    assert ".ts" in exts


def test_load_php_extracts_methods(php_fixture: Path):
    doc = CodeLoader().load(php_fixture)
    assert doc.language == "php"
    symbols = [b for b in doc.blocks if b.kind == "code_function"]
    names = [b.extra["symbol"] for b in symbols]
    assert "login" in names
    assert "helper" in names


def test_load_python_extracts_class_methods(py_fixture: Path):
    doc = CodeLoader().load(py_fixture)
    assert doc.language == "python"
    classes = [b for b in doc.blocks if b.kind == "code_class"]
    funcs = [b for b in doc.blocks if b.kind == "code_function"]
    assert any(b.extra["symbol"] == "Foo" for b in classes)
    assert any(b.extra["symbol"] == "greet" for b in funcs)


def test_blocks_have_line_numbers(php_fixture: Path):
    doc = CodeLoader().load(php_fixture)
    for b in doc.blocks:
        assert b.start_line >= 1
        assert b.end_line >= b.start_line


@pytest.fixture
def php_fixture() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample.php"


@pytest.fixture
def py_fixture() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample.py"
