from pathlib import Path

from kb_core.utils.hashing import content_hash, sha256_of_bytes, sha256_of_file


def test_sha256_of_bytes_stable():
    assert sha256_of_bytes(b"hello") == sha256_of_bytes(b"hello")


def test_sha256_of_bytes_differs():
    assert sha256_of_bytes(b"hello") != sha256_of_bytes(b"world")


def test_sha256_of_file_streams(tmp_path: Path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"x" * 1024 * 1024)
    h = sha256_of_file(p)
    assert len(h) == 64


def test_content_hash_matches_sha():
    text = "some chunk content"
    assert content_hash(text) == sha256_of_bytes(text.encode("utf-8"))


def test_sha256_of_file_missing_raises(tmp_path: Path):
    import pytest
    with pytest.raises(FileNotFoundError):
        sha256_of_file(tmp_path / "nope.bin")
