from deepresearch.retrieval.lexical import (
    LexicalPolicy,
    configure_lexical_policy,
    get_lexical_policy,
    lexical_tokens,
)


def test_builtin_policy_keeps_cjk_unigrams_and_bigrams():
    policy = LexicalPolicy(tokenizer="builtin")

    tokens = policy.tokenize("检索增强生成")

    assert "检" in tokens
    assert "检索" in tokens
    assert "检索增强生成" not in tokens


def test_jieba_policy_uses_project_userdict():
    policy = LexicalPolicy(tokenizer="jieba", cjk_ngram_fallback=False)

    tokens = policy.tokenize("检索增强生成能够提升RAG系统")

    assert "检索增强生成" in tokens
    assert "rag" in tokens


def test_jieba_policy_can_keep_cjk_ngram_fallback():
    policy = LexicalPolicy(tokenizer="jieba", cjk_ngram_fallback=True)

    tokens = policy.tokenize("多智能体")

    assert "多智能体" in tokens
    assert "多智" in tokens


def test_configure_lexical_policy_updates_default_entrypoint():
    original = get_lexical_policy()
    try:
        configure_lexical_policy(
            LexicalPolicy(tokenizer="jieba", cjk_ngram_fallback=False)
        )

        tokens = lexical_tokens("大语言模型")

        assert "大语言模型" in tokens
    finally:
        configure_lexical_policy(original)
