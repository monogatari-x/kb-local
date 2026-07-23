class KBError(Exception):
    def __init__(
        self,
        message: str,
        *,
        recoverable: bool = True,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.recoverable = recoverable
        self.cause = cause


class ConfigError(KBError):
    pass


class ModelLoadError(KBError):
    pass


class FilePathError(KBError):
    pass


class FileTooLargeError(KBError):
    pass


class UnsupportedFileTypeError(KBError):
    pass


class ParseError(KBError):
    def __init__(self, message: str, *, file_type: str, cause: Exception | None = None):
        super().__init__(message, recoverable=True, cause=cause)
        self.file_type = file_type


class EmbeddingError(KBError):
    pass


class VectorStoreError(KBError):
    pass


class SQLiteError(KBError):
    pass


class CacheMissError(KBError):
    pass


class DuplicateWatchDirError(KBError):
    pass


class ProjectConflictError(KBError):
    pass
