from kb_core.embeddings.device import cuda_available, resolve_device


def test_resolve_cpu_returns_cpu():
    assert resolve_device("cpu") == "cpu"


def test_resolve_cuda_when_unavailable_falls_back():
    if cuda_available():
        assert resolve_device("cuda") == "cuda"
    else:
        assert resolve_device("cuda") == "cpu"


def test_resolve_auto_picks_cpu_in_ci():
    d = resolve_device("auto")
    assert d in {"cuda", "cpu"}


def test_resolve_invalid_falls_back_cpu():
    assert resolve_device("quantum") == "cpu"
