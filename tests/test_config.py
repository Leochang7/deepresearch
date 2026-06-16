from pathlib import Path

from deepresearch.config import DeepResearchConfig, load_config


class TestDeepResearchConfig:
    def test_default_config_valid(self):
        cfg = DeepResearchConfig()
        assert cfg.llm.provider == "mimo"
        assert cfg.llm.model == "mimo-v2.5-pro"
        assert cfg.llm.api_key_prefix == ""
        assert cfg.llm.api_key_required is True
        assert cfg.llm.max_tokens_field == "max_completion_tokens"
        assert cfg.embedding.dim == 1024
        assert cfg.chunking.chunk_size_chars == 1200
        assert cfg.executor.max_concurrency == 4

    def test_nested_sections_exist(self):
        cfg = DeepResearchConfig()
        assert hasattr(cfg, "llm")
        assert hasattr(cfg, "embedding")
        assert hasattr(cfg, "reranker")
        assert hasattr(cfg, "milvus")
        assert hasattr(cfg, "retrieval")
        assert hasattr(cfg, "web_search")
        assert hasattr(cfg, "mimo_search")
        assert hasattr(cfg, "fetch")
        assert hasattr(cfg, "chunking")
        assert hasattr(cfg, "dedup")
        assert hasattr(cfg, "executor")
        assert hasattr(cfg, "red_blue")
        assert hasattr(cfg, "synthesizer")
        assert hasattr(cfg, "evidence_quality")
        assert hasattr(cfg, "fusion")

    def test_benchmark_config_defaults(self):
        from deepresearch.config import BenchmarkConfig

        cfg = BenchmarkConfig()
        assert cfg.max_concurrency == 1


class TestConfigFromFile:
    def test_load_from_toml_file(self, tmp_path):
        toml_content = """
[llm]
provider = "deepseek"
model = "deepseek-chat"

[executor]
max_concurrency = 8
"""
        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(toml_content)

        cfg = DeepResearchConfig.from_toml(cfg_path)
        assert cfg.llm.provider == "deepseek"
        assert cfg.llm.model == "deepseek-chat"
        assert cfg.executor.max_concurrency == 8
        # Other fields keep defaults
        assert cfg.embedding.dim == 1024

    def test_partial_config_uses_defaults(self, tmp_path):
        toml_content = """
[milvus]
uri = "/custom/path.db"
"""
        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(toml_content)

        cfg = DeepResearchConfig.from_toml(cfg_path)
        assert cfg.milvus.uri == "/custom/path.db"
        assert cfg.milvus.metric_type == "COSINE"


class TestEnvVarOverride:
    def test_langfuse_config_prompt_defaults(self):
        from deepresearch.config import LangfuseConfig

        cfg = LangfuseConfig()
        assert cfg.prompt_provider == "local"
        assert cfg.prompt_label == "production"

    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv("DEEPRESEARCH_LLM_PROVIDER", "deepseek")
        monkeypatch.setenv("DEEPRESEARCH_LLM_MODEL", "deepseek-chat")
        monkeypatch.setenv("DEEPRESEARCH_LLM_API_KEY_HEADER", "Authorization")
        monkeypatch.setenv("DEEPRESEARCH_LLM_API_KEY_PREFIX", "Bearer ")
        monkeypatch.setenv("DEEPRESEARCH_LLM_API_KEY_REQUIRED", "false")
        monkeypatch.setenv("DEEPRESEARCH_LLM_MAX_TOKENS_FIELD", "max_tokens")
        monkeypatch.setenv("DEEPRESEARCH_MILVUS_URI", "/env/path.db")
        monkeypatch.setenv("DEEPRESEARCH_MILVUS_CHUNKS_COLLECTION", "chunks_env")
        monkeypatch.setenv("DEEPRESEARCH_MILVUS_MEMORIES_COLLECTION", "memories_env")

        cfg = DeepResearchConfig.from_env()
        assert cfg.llm.provider == "deepseek"
        assert cfg.llm.model == "deepseek-chat"
        assert cfg.llm.api_key_header == "Authorization"
        assert cfg.llm.api_key_prefix == "Bearer "
        assert cfg.llm.api_key_required is False
        assert cfg.llm.max_tokens_field == "max_tokens"
        assert cfg.milvus.uri == "/env/path.db"
        assert cfg.milvus.chunks_collection == "chunks_env"
        assert cfg.milvus.memories_collection == "memories_env"

    def test_secret_values_do_not_override_api_key_env_names(self, monkeypatch):
        monkeypatch.setenv("DEEPRESEARCH_EMBEDDING_API_KEY", "secret-embedding")
        monkeypatch.setenv("DEEPRESEARCH_RERANKER_API_KEY", "secret-reranker")
        monkeypatch.setenv("TAVILY_API_KEY", "secret-tavily")

        cfg = DeepResearchConfig.from_env()

        assert cfg.embedding.api_key_env == "DEEPRESEARCH_EMBEDDING_API_KEY"
        assert cfg.reranker.api_key_env == "DEEPRESEARCH_RERANKER_API_KEY"
        assert cfg.web_search.api_key_env == "TAVILY_API_KEY"

    def test_pm2_env_overrides(self, monkeypatch):
        monkeypatch.setenv("DEEPRESEARCH_REPORT_PROFILE", "timeline")
        monkeypatch.setenv("DEEPRESEARCH_EVIDENCE_MIN_CONFIDENCE", "0.55")
        monkeypatch.setenv("DEEPRESEARCH_EVIDENCE_MIN_TOKEN_OVERLAP", "0.25")

        cfg = DeepResearchConfig.from_env()

        assert cfg.synthesizer.report_profile == "timeline"
        assert cfg.evidence_quality.min_confidence == 0.55
        assert cfg.evidence_quality.min_token_overlap == 0.25

    def test_fusion_env_overrides(self, monkeypatch):
        monkeypatch.setenv("DEEPRESEARCH_RRF_K", "42")
        monkeypatch.setenv("DEEPRESEARCH_MAX_FUSED_DOCS", "15")
        monkeypatch.setenv("DEEPRESEARCH_MAX_FUSED_CHUNKS", "25")
        monkeypatch.setenv("DEEPRESEARCH_MMR_LAMBDA", "0.6")
        monkeypatch.setenv("DEEPRESEARCH_MAX_MMR_RESULTS", "10")

        cfg = DeepResearchConfig.from_env()

        assert cfg.fusion.rrf_k == 42
        assert cfg.fusion.max_fused_docs == 15
        assert cfg.fusion.max_fused_chunks == 25
        assert cfg.fusion.mmr_lambda == 0.6
        assert cfg.fusion.max_mmr_results == 10

    def test_langfuse_env_overrides(self, monkeypatch):
        monkeypatch.setenv("DEEPRESEARCH_LANGFUSE_ENABLED", "true")
        monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000")
        monkeypatch.setenv("DEEPRESEARCH_EXPERIMENT_NAME", "pm6-test")

        cfg = DeepResearchConfig.from_env()

        assert cfg.langfuse.enabled is True
        assert cfg.langfuse.host == "http://localhost:3000"
        assert cfg.langfuse.experiment_name == "pm6-test"


class TestLoadConfig:
    def test_default_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DEEPRESEARCH_CONFIG_PATH", raising=False)
        cfg = load_config(config_path=None, cwd=tmp_path)
        assert cfg.llm.provider == "mimo"

    def test_explicit_config_path(self, tmp_path):
        toml_content = """
[llm]
provider = "test_provider"
"""
        cfg_path = tmp_path / "custom.toml"
        cfg_path.write_text(toml_content)

        cfg = load_config(config_path=str(cfg_path))
        assert cfg.llm.provider == "test_provider"

    def test_env_path_overrides_cwd(self, tmp_path, monkeypatch):
        toml_content = """
[llm]
provider = "env_provider"
"""
        cfg_path = tmp_path / "env_config.toml"
        cfg_path.write_text(toml_content)
        monkeypatch.setenv("DEEPRESEARCH_CONFIG_PATH", str(cfg_path))

        cfg = load_config(config_path=None, cwd=Path("/nonexistent"))
        assert cfg.llm.provider == "env_provider"

    def test_cwd_config_toml(self, tmp_path):
        toml_content = """
[llm]
provider = "cwd_provider"
"""
        (tmp_path / "config.toml").write_text(toml_content)

        cfg = load_config(config_path=None, cwd=tmp_path)
        assert cfg.llm.provider == "cwd_provider"

    def test_priority_cli_over_file_over_env(self, tmp_path, monkeypatch):
        toml_content = """
[llm]
provider = "file_provider"
model = "file_model"
"""
        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(toml_content)

        monkeypatch.setenv("DEEPRESEARCH_LLM_PROVIDER", "env_provider")

        cfg = load_config(
            config_path=str(cfg_path),
            cli_overrides={"llm": {"model": "cli_model"}},
        )
        assert cfg.llm.provider == "file_provider"
        assert cfg.llm.model == "cli_model"


def test_model_config_files_exist():
    models_dir = Path("examples/configs/models")
    assert models_dir.is_dir()
    configs = list(models_dir.glob("*.toml"))
    assert len(configs) >= 4
    names = {c.stem for c in configs}
    assert "mimo" in names
    assert "deepseek" in names
    assert "openai" in names
    assert "vllm" in names


def test_model_configs_parse():
    for toml_path in Path("examples/configs/models").glob("*.toml"):
        cfg = DeepResearchConfig.from_toml(toml_path)
        assert cfg.llm.provider in ("mimo", "deepseek", "openai_compatible")
        if cfg.llm.provider in {"deepseek", "openai_compatible"}:
            assert cfg.llm.max_tokens_field == "max_tokens"
        if toml_path.stem == "vllm":
            assert cfg.llm.api_key_env == ""
            assert cfg.llm.api_key_header == ""
            assert cfg.llm.api_key_prefix == ""
            assert cfg.llm.api_key_required is False
        elif cfg.llm.provider in {"deepseek", "openai_compatible"}:
            assert cfg.llm.api_key_header == "Authorization"
            assert cfg.llm.api_key_prefix == "Bearer "
            assert cfg.llm.api_key_required is True
