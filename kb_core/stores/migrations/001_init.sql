CREATE TABLE IF NOT EXISTS documents (
    doc_id           TEXT PRIMARY KEY,
    source_path      TEXT NOT NULL,
    rel_path         TEXT NOT NULL,
    project          TEXT NOT NULL,
    file_type        TEXT NOT NULL,
    language         TEXT,
    sha256           TEXT NOT NULL,
    size_bytes       INTEGER NOT NULL,
    mtime            TEXT NOT NULL,
    ingested_at      TEXT NOT NULL,
    indexed_at       TEXT,
    embedding_version TEXT,
    parser_version   TEXT,
    status           TEXT NOT NULL DEFAULT 'active',
    error_msg        TEXT,
    tags             TEXT,
    meta             TEXT
);
CREATE INDEX IF NOT EXISTS idx_doc_sha256  ON documents(sha256);
CREATE INDEX IF NOT EXISTS idx_doc_project ON documents(project);
CREATE INDEX IF NOT EXISTS idx_doc_status  ON documents(status);
CREATE INDEX IF NOT EXISTS idx_doc_source  ON documents(source_path);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id         TEXT PRIMARY KEY,
    doc_id           TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    ordinal          INTEGER NOT NULL,
    text             TEXT NOT NULL,
    text_truncated   TEXT,
    tokens           INTEGER NOT NULL,
    content_hash     TEXT NOT NULL,
    start_char       INTEGER,
    end_char         INTEGER,
    start_line       INTEGER,
    end_line         INTEGER,
    section_path     TEXT,
    symbol_path      TEXT,
    chunk_type       TEXT NOT NULL,
    quality_score    REAL,
    language         TEXT,
    meta             TEXT,
    UNIQUE(doc_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_chunk_doc  ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunk_hash ON chunks(content_hash);
CREATE INDEX IF NOT EXISTS chunk_doc_ord  ON chunks(doc_id, ordinal);

CREATE TABLE IF NOT EXISTS watch_dirs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    path             TEXT NOT NULL UNIQUE,
    project_name     TEXT NOT NULL,
    project_strategy TEXT NOT NULL DEFAULT 'fixed',
    file_types       TEXT,
    exclude_patterns TEXT,
    recursive        INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL,
    last_scan_at     TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id           TEXT PRIMARY KEY,
    type             TEXT NOT NULL,
    status           TEXT NOT NULL,
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    total_files      INTEGER,
    processed_files  INTEGER DEFAULT 0,
    failed_files     INTEGER DEFAULT 0,
    error_log        TEXT,
    trigger          TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS tags (
    name             TEXT PRIMARY KEY,
    color            TEXT,
    description      TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key              TEXT PRIMARY KEY,
    value            TEXT,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embedding_cache (
    content_hash     TEXT NOT NULL,
    embedding_version TEXT NOT NULL,
    dense_vector     BLOB NOT NULL,
    sparse_indices   BLOB,
    sparse_values    BLOB,
    created_at       TEXT NOT NULL,
    PRIMARY KEY (content_hash, embedding_version)
);
