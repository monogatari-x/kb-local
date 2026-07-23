from abc import ABC, abstractmethod

from kb_core.loaders.base import LoadedDocument
from kb_core.models import Chunk


class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, loaded: LoadedDocument) -> list[Chunk]:
        ...
