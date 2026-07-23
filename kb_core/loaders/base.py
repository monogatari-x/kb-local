from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Block:
    text: str
    start_line: int
    end_line: int
    kind: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedDocument:
    text: str
    language: str | None
    blocks: list[Block]
    meta: dict[str, Any] = field(default_factory=dict)


class BaseLoader(ABC):
    @abstractmethod
    def supported_extensions(self) -> set[str]:
        ...

    @abstractmethod
    def load(self, path: Path) -> LoadedDocument:
        ...
