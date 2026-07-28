from enum import StrEnum


class FileType(StrEnum):
    CODE = "code"
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    IMAGE = "image"
    HTML = "html"


class DocStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    ERROR = "error"


class ChunkType(StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    CODE_FUNCTION = "code_function"
    CODE_CLASS = "code_class"
    CODE_STATEMENT = "code_statement"
    TABLE = "table"
    LIST = "list"
    IMAGE_CAPTION = "image_caption"
    MIXED = "mixed"


class ProjectStrategy(StrEnum):
    FIXED = "fixed"
    FIRST_SUBDIR = "first_subdir"
