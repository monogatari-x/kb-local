from kb_core.utils.tokens import count_tokens, count_tokens_batch


def test_english_tokens():
    assert count_tokens("hello world") == 2


def test_chinese_tokens():
    n = count_tokens("你好")
    assert 1 <= n <= 4


def test_empty_text():
    assert count_tokens("") == 0


def test_batch_consistent():
    texts = ["a", "bb", "ccc"]
    batch = count_tokens_batch(texts)
    one_by_one = [count_tokens(t) for t in texts]
    assert batch == one_by_one
