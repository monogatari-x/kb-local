from kb_core.loaders.base import BaseLoader


class LoaderRegistry:
    def __init__(self) -> None:
        self._by_ext: dict[str, BaseLoader] = {}

    def register(self, loader: BaseLoader) -> None:
        for ext in loader.supported_extensions():
            self._by_ext[ext.lower()] = loader

    def get_for_extension(self, ext: str) -> BaseLoader | None:
        return self._by_ext.get(ext.lower())

    def all_extensions(self) -> set[str]:
        return set(self._by_ext.keys())
