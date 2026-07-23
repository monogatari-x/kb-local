from pathlib import Path

from markdown_it import MarkdownIt

from kb_core.exceptions import FilePathError
from kb_core.loaders.base import BaseLoader, Block, LoadedDocument


class MarkdownLoader(BaseLoader):
    def __init__(self) -> None:
        self._md = MarkdownIt("commonmark", {"html": True}).enable("strikethrough")

    def supported_extensions(self) -> set[str]:
        return {".md", ".markdown"}

    def load(self, path: Path) -> LoadedDocument:
        if not path.exists():
            raise FilePathError(f"Markdown file not found: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        return LoadedDocument(
            text=text,
            language="markdown",
            blocks=self._extract_blocks(text),
            meta={},
        )

    def _extract_blocks(self, text: str) -> list[Block]:
        blocks: list[Block] = []
        lines = text.splitlines()
        line_offset = 0
        for token in self._md.parse(text):
            start_line = token.map[0] + 1 if token.map else line_offset
            end_line = token.map[1] if token.map else line_offset
            if token.type == "heading_open":
                level = int(token.tag[1:])
                blocks.append(Block(
                    text="",
                    start_line=start_line,
                    end_line=end_line,
                    kind="heading",
                    extra={"level": level, "title": ""},
                ))
            elif token.type == "inline":
                if blocks and blocks[-1].kind == "heading" and not blocks[-1].extra["title"]:
                    blocks[-1].extra["title"] = token.content
                line_offset = end_line
            elif token.type == "fence":
                blocks.append(Block(
                    text=token.content,
                    start_line=start_line,
                    end_line=end_line,
                    kind="code_block",
                    extra={"language": token.info.strip() or "text"},
                ))
            elif token.type == "paragraph_open":
                line_offset = end_line
        return self._fill_paragraph_text(blocks, lines)

    def _fill_paragraph_text(self, blocks: list[Block], lines: list[str]) -> list[Block]:
        return blocks
