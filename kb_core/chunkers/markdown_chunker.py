import uuid

from kb_core.chunkers.base import BaseChunker
from kb_core.chunkers.recursive_chunker import RecursiveChunker
from kb_core.enums import ChunkType
from kb_core.loaders.base import Block, LoadedDocument
from kb_core.models import Chunk
from kb_core.utils.hashing import content_hash
from kb_core.utils.tokens import count_tokens


class MarkdownChunker(BaseChunker):
    def __init__(self, max_tokens: int = 512, overlap: int = 50) -> None:
        self._recursive = RecursiveChunker(max_tokens=max_tokens, overlap=overlap)

    def chunk(self, loaded: LoadedDocument) -> list[Chunk]:
        out: list[Chunk] = []
        ordinal = 0
        for block in loaded.blocks:
            if block.kind == "heading":
                out.append(self._make_heading_chunk(block, loaded.text, ordinal))
                ordinal += 1
            elif block.kind == "code_block":
                out.append(self._make_code_chunk(block, loaded.text, ordinal))
                ordinal += 1
        para_loaded = LoadedDocument(
            text=loaded.text,
            language=loaded.language,
            blocks=[b for b in loaded.blocks if b.kind == "paragraph"],
            meta=loaded.meta,
        )
        for c in self._recursive.chunk(para_loaded):
            c.ordinal = ordinal
            ordinal += 1
            out.append(c)
        return out

    def _make_heading_chunk(self, block: Block, full_text: str, ordinal: int) -> Chunk:
        title = block.extra.get("title", "")
        text = title or ""
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id="",
            ordinal=ordinal,
            text=text,
            tokens=count_tokens(text),
            content_hash=content_hash(text),
            start_char=full_text.find(text) if text else 0,
            end_char=(full_text.find(text) + len(text)) if text else 0,
            start_line=block.start_line,
            end_line=block.end_line,
            section_path=title or None,
            chunk_type=ChunkType.HEADING,
            quality_score=0.9,
            language="markdown",
        )

    def _make_code_chunk(self, block: Block, full_text: str, ordinal: int) -> Chunk:
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
            chunk_type=ChunkType.MIXED,
            quality_score=1.0,
            language=block.extra.get("language", "text"),
            meta={"original_kind": "code_block"},
        )
