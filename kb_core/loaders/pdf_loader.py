from pathlib import Path

from pypdf import PdfReader

from kb_core.exceptions import FilePathError
from kb_core.loaders.base import BaseLoader, Block, LoadedDocument


class PDFLoader(BaseLoader):
    def supported_extensions(self) -> set[str]:
        return {".pdf"}

    def load(self, path: Path) -> LoadedDocument:
        if not path.exists():
            raise FilePathError(f"PDF file not found: {path}")
        reader = PdfReader(str(path))
        blocks: list[Block] = []
        all_text: list[str] = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            blocks.append(
                Block(
                    text=text,
                    start_line=page_num,
                    end_line=page_num,
                    kind="page",
                    extra={"page": page_num},
                )
            )
            all_text.append(text)
        return LoadedDocument(
            text="\n\n".join(all_text),
            language=None,
            blocks=blocks,
            meta={"page_count": len(reader.pages)},
        )
