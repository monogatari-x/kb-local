import uuid

from kb_core.chunkers.base import BaseChunker
from kb_core.chunkers.recursive_chunker import RecursiveChunker
from kb_core.enums import ChunkType
from kb_core.loaders.base import Block, LoadedDocument
from kb_core.models import Chunk
from kb_core.utils.hashing import content_hash
from kb_core.utils.tokens import count_tokens


class CodeChunker(BaseChunker):
    def __init__(self, max_tokens: int = 800) -> None:
        self.max_tokens = max_tokens
        self._recursive = RecursiveChunker(max_tokens=max_tokens, overlap=0)

    def chunk(self, loaded: LoadedDocument) -> list[Chunk]:
        out: list[Chunk] = []
        ordinal = 0
        for block in loaded.blocks:
            chunk_type = (ChunkType.CODE_FUNCTION if block.kind == "code_function"
                          else ChunkType.CODE_CLASS if block.kind == "code_class"
                          else ChunkType.CODE_STATEMENT if block.kind == "code_statement"
                          else None)
            if chunk_type is None:
                continue
            if count_tokens(block.text) <= self.max_tokens:
                out.append(self._make_chunk(block, loaded.text, ordinal, chunk_type))
                ordinal += 1
            else:
                sub_loaded = LoadedDocument(
                    text=block.text, language=loaded.language,
                    blocks=[Block(text=block.text, start_line=block.start_line,
                                  end_line=block.end_line, kind="paragraph")],
                    meta={},
                )
                for c in self._recursive.chunk(sub_loaded):
                    c.ordinal = ordinal
                    c.chunk_type = chunk_type
                    c.symbol_path = block.extra.get("symbol")
                    c.language = loaded.language
                    out.append(c)
                    ordinal += 1
        return out

    def _make_chunk(self, block: Block, full_text: str, ordinal: int,
                    chunk_type: ChunkType) -> Chunk:
        text = block.text
        start_char = full_text.find(text)
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id="",
            ordinal=ordinal,
            text=text,
            tokens=count_tokens(text),
            content_hash=content_hash(text),
            start_char=start_char if start_char >= 0 else 0,
            end_char=(start_char + len(text)) if start_char >= 0 else len(text),
            start_line=block.start_line,
            end_line=block.end_line,
            symbol_path=block.extra.get("symbol"),
            chunk_type=chunk_type,
            quality_score=1.0,
            language=block.extra.get("language"),
        )
