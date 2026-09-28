import pytest

from kb_core.exceptions import (
    ConfigError,
    EmbeddingError,
    FileTooLargeError,
    KBError,
    ParseError,
    ProjectConflictError,
    UnsupportedFileTypeError,
    VectorStoreError,
)


def test_kb_error_defaults():
    err = KBError("boom")
    assert str(err) == "boom"
    assert err.recoverable is True
    assert err.cause is None


def test_kb_error_with_cause():
    cause = ValueError("inner")
    err = KBError("outer", recoverable=False, cause=cause)
    assert err.recoverable is False
    assert err.cause is cause


def test_subclass_is_kb_error():
    for cls in [
        ConfigError,
        EmbeddingError,
        FileTooLargeError,
        UnsupportedFileTypeError,
        ParseError,
        VectorStoreError,
        ProjectConflictError,
    ]:
        assert issubclass(cls, KBError)


def test_parse_error_with_file_type():
    err = ParseError("bad pdf", file_type="pdf")
    assert err.file_type == "pdf"
    assert err.recoverable is True


def test_raise_and_catch_as_base():
    with pytest.raises(KBError):
        raise ConfigError("missing key")
