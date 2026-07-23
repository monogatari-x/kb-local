import pytest

from kb_core.chunkers.base import BaseChunker
from kb_core.loaders.base import LoadedDocument


def test_base_cannot_instantiate():
    with pytest.raises(TypeError):
        BaseChunker()


def test_concrete_subclass_works():
    class Dummy(BaseChunker):
        def chunk(self, loaded):
            return []

    d = Dummy()
    assert d.chunk(LoadedDocument(text="", language=None, blocks=[], meta={})) == []
