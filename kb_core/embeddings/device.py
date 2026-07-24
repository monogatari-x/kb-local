def cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def cuda_free_memory_mb() -> int | None:
    if not cuda_available():
        return None
    try:
        import torch
        free, _total = torch.cuda.mem_get_info()
        return int(free / 1024 / 1024)
    except Exception:
        return None


def resolve_device(preference: str = "auto") -> str:
    if preference == "cpu":
        return "cpu"
    if preference == "cuda":
        return "cuda" if cuda_available() else "cpu"
    if cuda_available():
        free = cuda_free_memory_mb()
        if free is None or free >= 1024:
            return "cuda"
    return "cpu"
