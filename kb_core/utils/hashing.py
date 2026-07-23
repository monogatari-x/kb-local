import hashlib
from pathlib import Path

CHUNK = 1024 * 1024


def sha256_of_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(text: str) -> str:
    return sha256_of_bytes(text.encode("utf-8"))
