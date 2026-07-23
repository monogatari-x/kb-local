from pathlib import Path

from kb_core.exceptions import FilePathError
from kb_core.loaders.base import BaseLoader, Block, LoadedDocument


class TextLoader(BaseLoader):
    def supported_extensions(self) -> set[str]:
        return {".txt", ".log", ".csv", ".tsv"}

    def load(self, path: Path) -> LoadedDocument:
        if not path.exists():
            raise FilePathError(f"Text file not found: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        blocks: list[Block] = []
        lines = text.splitlines()
        current: list[str] = []
        start_line = 1
        for i, line in enumerate(lines, start=1):
            if line.strip() == "":
                if current:
                    blocks.append(Block(
                        text="\n".join(current),
                        start_line=start_line,
                        end_line=i - 1,
                        kind="paragraph",
                    ))
                    current = []
                start_line = i + 1
            else:
                if not current:
                    start_line = i
                current.append(line)
        if current:
            blocks.append(Block(
                text="\n".join(current),
                start_line=start_line,
                end_line=len(lines),
                kind="paragraph",
            ))
        return LoadedDocument(text=text, language=None, blocks=blocks, meta={})
