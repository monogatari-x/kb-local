import tiktoken

_ENCOD = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    if not text:
        return 0
    enc = _ENCOD if encoding == "cl100k_base" else tiktoken.get_encoding(encoding)
    return len(enc.encode(text))


def count_tokens_batch(texts: list[str], encoding: str = "cl100k_base") -> list[int]:
    enc = _ENCOD if encoding == "cl100k_base" else tiktoken.get_encoding(encoding)
    return [len(enc.encode(t)) for t in texts]
