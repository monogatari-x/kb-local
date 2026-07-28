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


def test_load_python_captures_top_level_imports(py_fixture: Path):
    doc = CodeLoader().load(py_fixture)
    statements = [b for b in doc.blocks if b.kind == "code_statement"]
    assert len(statements) >= 1
    joined = "\n".join(b.text for b in statements)
    assert "import os" in joined
    assert "import sys" in joined


def test_load_python_captures_top_level_assignment(py_fixture: Path):
    doc = CodeLoader().load(py_fixture)
    statements = [b for b in doc.blocks if b.kind == "code_statement"]
    joined = "\n".join(b.text for b in statements)
    assert "DEBUG = True" in joined
    assert "TIMEOUT = 30" in joined


def test_load_python_pure_config_file_not_empty(config_fixture: Path):
    doc = CodeLoader().load(config_fixture)
    assert len(doc.blocks) > 0
    assert all(b.kind != "code_function" for b in doc.blocks)
    assert all(b.kind != "code_class" for b in doc.blocks)


def test_load_python_captures_if_main_block(py_fixture: Path):
    doc = CodeLoader().load(py_fixture)
    statements = [b for b in doc.blocks if b.kind == "code_statement"]
    joined = "\n".join(b.text for b in statements)
    assert 'if __name__ ==' in joined
    assert "sys.exit(0)" in joined


@pytest.fixture
def php_fixture() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample.php"


@pytest.fixture
def py_fixture() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample.py"


@pytest.fixture
def config_fixture() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample_config.py"
