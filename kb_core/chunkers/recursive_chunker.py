import uuid

from kb_core.chunkers.base import BaseChunker
from kb_core.enums import ChunkType
from kb_core.loaders.base import Block, LoadedDocument
from kb_core.models import Chunk
from kb_core.utils.hashing import content_hash
from kb_core.utils.tokens import count_tokens

_SEPARATORS = ["\n\n", "\n", "。", ". ", "!", "?", ";", " ", ""]


class RecursiveChunker(BaseChunker):
    def __init__(self, max_tokens: int = 512, overlap: int = 50) -> None:
        self.max_tokens = max_tokens
        self.overlap = overlap

    def chunk(self, loaded: LoadedDocument) -> list[Chunk]:
        out: list[Chunk] = []
        ordinal = 0
        for block in loaded.blocks:
            if block.kind != "paragraph":
                continue
            for piece, line_start in self._split_block(block):
                tokens = count_tokens(piece)
                start_char = loaded.text.find(piece)
                end_char = start_char + len(piece)
                out.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id="",
                    ordinal=ordinal,
                    text=piece,
                    tokens=tokens,
                    content_hash=content_hash(piece),
                    start_char=start_char if start_char >= 0 else 0,
                    end_char=end_char if start_char >= 0 else len(piece),
                    start_line=line_start,
                    end_line=line_start + piece.count("\n"),
                    chunk_type=ChunkType.PARAGRAPH,
                    quality_score=1.0 if tokens >= 32 else 0.6,
                    language=loaded.language,
                ))
                ordinal += 1
        return out

    def _split_block(self, block: Block) -> list[tuple[str, int]]:
        text = block.text
        if count_tokens(text) <= self.max_tokens:
            return [(text, block.start_line)]
        return self._recursive_split(text, block.start_line)

    def _recursive_split(self, text: str, base_line: int) -> list[tuple[str, int]]:
        if count_tokens(text) <= self.max_tokens or not text:
            return [(text, base_line)]
        for sep in _SEPARATORS:
            if sep and sep in text:
                parts = text.split(sep)
                pieces: list[tuple[str, int]] = []
                current = ""
                current_line = base_line
                consumed_lines = 0
                for part in parts:
                    candidate = (current + sep + part) if current else part
                    if count_tokens(candidate) <= self.max_tokens:
                        current = candidate
                    else:
                        if current:
                            pieces.append((current, current_line))
                            consumed_lines += current.count("\n")
                            current_line = base_line + consumed_lines
                        if count_tokens(part) > self.max_tokens:
                            sub = self._recursive_split(part, current_line)
                            pieces.extend(sub)
                            consumed_lines += part.count("\n")
                            current_line = base_line + consumed_lines
                            current = ""
                        else:
                            current = part
                if current:
                    pieces.append((current, current_line))
                return self._apply_overlap(pieces)
        return [(text, base_line)]

    def _apply_overlap(self, pieces: list[tuple[str, int]]) -> list[tuple[str, int]]:
        if self.overlap <= 0 or len(pieces) < 2:
            return pieces
        out: list[tuple[str, int]] = [pieces[0]]
        for i in range(1, len(pieces)):
            prev_text = pieces[i - 1][0]
            tail = prev_text[-self.overlap * 4:]
            merged = tail + pieces[i][0]
            out.append((merged, pieces[i][1]))
        return out
