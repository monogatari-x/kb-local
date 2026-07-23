from enum import Enum


class FileType(str, Enum):
    CODE = "code"
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    IMAGE = "image"
    HTML = "html"


class DocStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    ERROR = "error"


class ChunkType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    CODE_FUNCTION = "code_function"
    CODE_CLASS = "code_class"
    TABLE = "table"
    LIST = "list"
    IMAGE_CAPTION = "image_caption"
    MIXED = "mixed"


class ProjectStrategy(str, Enum):
    FIXED = "fixed"
    FIRST_SUBDIR = "first_subdir"
