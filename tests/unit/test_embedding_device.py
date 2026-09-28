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
    assert d in {"cuda", "mps", "cpu"}


def test_resolve_invalid_falls_back_cpu():
    assert resolve_device("quantum") == "cpu"


def test_resolve_mps_when_unavailable_falls_back(monkeypatch):
    monkeypatch.setattr("kb_core.embeddings.device.mps_available", lambda: False)
    assert resolve_device("mps") == "cpu"


def test_resolve_mps_when_available(monkeypatch):
    monkeypatch.setattr("kb_core.embeddings.device.mps_available", lambda: True)
    assert resolve_device("mps") == "mps"


def test_resolve_auto_prefers_cuda_over_mps(monkeypatch):
    monkeypatch.setattr("kb_core.embeddings.device.cuda_available", lambda: True)
    monkeypatch.setattr("kb_core.embeddings.device.cuda_free_memory_mb", lambda: 4096)
    monkeypatch.setattr("kb_core.embeddings.device.mps_available", lambda: True)
    assert resolve_device("auto") == "cuda"


def test_resolve_auto_picks_mps_on_mac_without_cuda(monkeypatch):
    monkeypatch.setattr("kb_core.embeddings.device.cuda_available", lambda: False)
    monkeypatch.setattr("kb_core.embeddings.device.mps_available", lambda: True)
    assert resolve_device("auto") == "mps"


def test_resolve_auto_cpu_when_no_accelerator(monkeypatch):
    monkeypatch.setattr("kb_core.embeddings.device.cuda_available", lambda: False)
    monkeypatch.setattr("kb_core.embeddings.device.mps_available", lambda: False)
    assert resolve_device("auto") == "cpu"
