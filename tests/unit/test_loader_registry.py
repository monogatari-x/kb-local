from pathlib import Path

from kb_core.loaders.base import BaseLoader, Block, LoadedDocument
from kb_core.loaders.registry import LoaderRegistry


class FakeLoader(BaseLoader):
    def supported_extensions(self) -> set[str]:
        return {".txt"}

    def load(self, path: Path) -> LoadedDocument:
        return LoadedDocument(
            text="hi",
            language=None,
            blocks=[Block(text="hi", start_line=1, end_line=1, kind="paragraph")],
            meta={},
        )


def test_register_and_get() -> None:
    reg = LoaderRegistry()
    reg.register(FakeLoader())
    got = reg.get_for_extension(".txt")
    assert isinstance(got, FakeLoader)


def test_get_unknown_returns_none() -> None:
    reg = LoaderRegistry()
    assert reg.get_for_extension(".xyz") is None


def test_all_extensions() -> None:
    reg = LoaderRegistry()
    reg.register(FakeLoader())
    assert ".txt" in reg.all_extensions()


def test_duplicate_extension_overwrites() -> None:
    reg = LoaderRegistry()
    reg.register(FakeLoader())
    reg.register(FakeLoader())
    assert len(reg.all_extensions()) == 1
