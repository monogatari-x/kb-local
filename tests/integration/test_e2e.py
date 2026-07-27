"""E2E：完整跑通 add → search 流程。

需要 Docker（启动 Qdrant testcontainer）和 BGE-M3 模型权重。
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_e2e_add_and_search(qdrant_store_module, tmp_path_factory):
    from kb_core.chunkers.code_chunker import CodeChunker
    from kb_core.chunkers.markdown_chunker import MarkdownChunker
    from kb_core.chunkers.recursive_chunker import RecursiveChunker
    from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER
    from kb_core.loaders.code_loader import CodeLoader
    from kb_core.loaders.markdown_loader import MarkdownLoader
    from kb_core.loaders.registry import LoaderRegistry
    from kb_core.pipelines.indexing import IndexingPipeline
    from kb_core.pipelines.retrieval import RetrievalPipeline
    from kb_core.stores.sqlite_store import SQLiteStore

    tmp = tmp_path_factory.mktemp("e2e")
    store = SQLiteStore(tmp / "e2e.db")
    store.init_schema()

    reg = LoaderRegistry()
    reg.register(CodeLoader())
    reg.register(MarkdownLoader())

    embedder = BGE_M3_EMBEDDER(device="cpu", batch_size=4)
    chunkers = {"code": CodeChunker(), "markdown": MarkdownChunker(), "text": RecursiveChunker()}
    indexing = IndexingPipeline(store, qdrant_store_module, reg, embedder, chunkers)
    retrieval = RetrievalPipeline(store, qdrant_store_module, embedder)

    src = tmp / "Auth.php"
    src.write_text(
        """<?php
class AuthController {
    public function login($username, $password) {
        if ($this->verify($username, $password)) {
            return $this->createSession($username);
        }
        return false;
    }

    private function verify($u, $p) {
        return password_verify($p, $this->getHash($u));
    }
}
""",
        encoding="utf-8",
    )

    doc_id = indexing.index_file(
        src,
        watch_dir=tmp,
        project_strategy="first_subdir",
        project_name="e2e_app",
    )
    assert doc_id

    results = retrieval.search("用户登录认证", top_k=5)
    assert len(results) > 0
    top = results[0]
    assert top.chunk.symbol_path == "login"
    assert "Auth.php" in top.citation or "auth.php" in top.citation.lower()
    store.close()


def test_e2e_markdown_search(qdrant_store_module, tmp_path_factory):
    from kb_core.chunkers.markdown_chunker import MarkdownChunker
    from kb_core.chunkers.recursive_chunker import RecursiveChunker
    from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER
    from kb_core.loaders.markdown_loader import MarkdownLoader
    from kb_core.loaders.registry import LoaderRegistry
    from kb_core.pipelines.indexing import IndexingPipeline
    from kb_core.pipelines.retrieval import RetrievalPipeline
    from kb_core.stores.sqlite_store import SQLiteStore

    tmp = tmp_path_factory.mktemp("md_e2e")
    store = SQLiteStore(tmp / "md.db")
    store.init_schema()

    reg = LoaderRegistry()
    reg.register(MarkdownLoader())

    embedder = BGE_M3_EMBEDDER(device="cpu", batch_size=4)
    chunkers = {"markdown": MarkdownChunker(), "text": RecursiveChunker()}
    indexing = IndexingPipeline(store, qdrant_store_module, reg, embedder, chunkers)
    retrieval = RetrievalPipeline(store, qdrant_store_module, embedder)

    src = tmp / "rule.md"
    src.write_text(
        """# 用户登录规则

用户必须使用 LDAP 账号登录。失败 5 次锁定 30 分钟。

## 密码策略

密码至少 12 位，含大小写+数字+符号。
""",
        encoding="utf-8",
    )

    indexing.index_file(src, watch_dir=tmp, project_strategy="first_subdir", project_name="rules")
    results = retrieval.search("密码要求", top_k=5)
    assert len(results) > 0
    store.close()
