from pathlib import Path

from tree_sitter import Node
from tree_sitter_languages import get_parser

from kb_core.exceptions import FilePathError, UnsupportedFileTypeError
from kb_core.loaders.base import BaseLoader, Block, LoadedDocument

_EXT_TO_LANG = {
    ".php": "php",
    ".py": "python",
    ".java": "java",
    ".kt": "kotlin",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "c_sharp",
    ".rb": "ruby",
    ".lua": "lua",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
}

_FUNC_NODE_TYPES = {
    "function_definition", "function_declaration", "method_definition",
    "function_item", "method_declaration",
}
_CLASS_NODE_TYPES = {
    "class_definition", "class_declaration", "class_specifier",
}


class CodeLoader(BaseLoader):
    def supported_extensions(self) -> set[str]:
        return set(_EXT_TO_LANG.keys())

    def load(self, path: Path) -> LoadedDocument:
        if not path.exists():
            raise FilePathError(f"Code file not found: {path}")
        ext = path.suffix.lower()
        lang = _EXT_TO_LANG.get(ext)
        if lang is None:
            raise UnsupportedFileTypeError(f"No language for {ext}")
        text = path.read_text(encoding="utf-8", errors="replace")
        return LoadedDocument(
            text=text,
            language=lang,
            blocks=self._extract_symbols(text, lang),
            meta={"ext": ext},
        )

    def _extract_symbols(self, text: str, lang: str) -> list[Block]:
        try:
            parser = get_parser(lang)
        except Exception as e:
            raise UnsupportedFileTypeError(f"Cannot load parser for {lang}: {e}") from e
        tree = parser.parse(text.encode("utf-8"))
        blocks: list[Block] = []
        self._walk(tree.root_node, text, blocks)
        return blocks

    def _walk(self, node: Node, text: str, blocks: list[Block]) -> None:
        for child in node.children:
            if child.type in _FUNC_NODE_TYPES:
                blocks.append(self._make_block(child, text, kind="code_function"))
            elif child.type in _CLASS_NODE_TYPES:
                blocks.append(self._make_block(child, text, kind="code_class"))
                self._walk(child, text, blocks)
            else:
                self._walk(child, text, blocks)

    def _make_block(self, node: Node, text: str, kind: str) -> Block:
        symbol = self._extract_symbol_name(node)
        encoded = text.encode("utf-8")
        lines = encoded[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        return Block(
            text=lines,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            kind=kind,
            extra={"symbol": symbol},
        )

    def _extract_symbol_name(self, node: Node) -> str:
        for child in node.children:
            if child.type in {"identifier", "name", "property_identifier", "type_identifier"}:
                return child.text.decode("utf-8", errors="replace")
        return "<anonymous>"
