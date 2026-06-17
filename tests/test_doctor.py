from unittest.mock import patch

import pytest

from deepresearch.config import DeepResearchConfig
from deepresearch.doctor import (
    CheckResult,
    DoctorReport,
    _check_langfuse,
    _check_langfuse_prompts,
    _check_milvus,
    run_doctor,
)


class TestDoctor:
    def test_run_doctor_returns_report(self):
        report = run_doctor()
        assert isinstance(report, DoctorReport)
        assert len(report.checks) >= 4

    def test_checks_have_names(self):
        report = run_doctor()
        for check in report.checks:
            assert check.name
            assert check.message

    def test_env_check_without_key(self, monkeypatch):
        monkeypatch.delenv("MIMO_API_KEY", raising=False)
        report = run_doctor()
        mimo_check = next(c for c in report.checks if c.name == "MIMO_API_KEY")
        assert not mimo_check.ok
        assert "NOT set" in mimo_check.message

    def test_env_check_with_key(self, monkeypatch):
        monkeypatch.setenv("MIMO_API_KEY", "test-key-1234-abcd")
        report = run_doctor()
        mimo_check = next(c for c in report.checks if c.name == "MIMO_API_KEY")
        assert mimo_check.ok
        assert "test" in mimo_check.message
        assert "abcd" in mimo_check.message

    def test_env_key_not_exposed(self, monkeypatch):
        monkeypatch.setenv("MIMO_API_KEY", "supersecretkey123")
        report = run_doctor()
        mimo_check = next(c for c in report.checks if c.name == "MIMO_API_KEY")
        assert "supersecretkey123" not in mimo_check.message
        assert "****" in mimo_check.message

    def test_optional_env_missing_is_not_error(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        report = run_doctor()
        tavily_check = next(c for c in report.checks if c.name == "TAVILY_API_KEY")
        assert tavily_check.ok

    def test_all_ok_when_required_key_set(self, monkeypatch):
        monkeypatch.setenv("MIMO_API_KEY", "test-key-1234-abcd")
        monkeypatch.setenv("DEEPRESEARCH_EMBEDDING_API_KEY", "embed-key")
        monkeypatch.setenv("DEEPRESEARCH_RERANKER_API_KEY", "rerank-key")
        cfg = DeepResearchConfig.model_validate(
            {
                "embedding": {"base_url": "https://embedding.example/v1"},
                "reranker": {"base_url": "https://reranker.example/v1"},
            }
        )
        report = run_doctor(cfg)
        assert report.all_ok

    def test_config_checks_present(self):
        report = run_doctor()
        names = {c.name for c in report.checks}
        assert "llm_provider" in names
        assert "embedding_model" in names
        assert "reranker_model" in names
        assert "milvus_uri" in names
        assert "langfuse" in names

    def test_langfuse_prompt_provider_requires_enabled(self):
        cfg = DeepResearchConfig.model_validate(
            {"langfuse": {"enabled": False, "prompt_provider": "langfuse"}}
        )
        report = run_doctor(cfg)
        check = next(
            c for c in report.checks if c.name == "langfuse_prompt_provider_enabled"
        )
        assert not check.ok
        assert check.severity == "error"

    def test_langfuse_env_required_when_enabled(self, monkeypatch):
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        cfg = DeepResearchConfig.model_validate({"langfuse": {"enabled": True}})
        report = run_doctor(cfg)
        public_key = next(c for c in report.checks if c.name == "LANGFUSE_PUBLIC_KEY")
        secret_key = next(c for c in report.checks if c.name == "LANGFUSE_SECRET_KEY")
        assert not public_key.ok
        assert not secret_key.ok

    def test_missing_embedding_base_url_is_error(self):
        report = run_doctor(DeepResearchConfig())
        check = next(c for c in report.checks if c.name == "embedding_base_url")
        assert not check.ok
        assert check.severity == "error"

    def test_milvus_lite_uri_is_error(self):
        cfg = DeepResearchConfig.model_validate({"milvus": {"uri": "./data/test.db"}})
        report = run_doctor(cfg)
        check = next(c for c in report.checks if c.name == "milvus_uri_mode")
        assert not check.ok
        assert "Standalone" in check.message

    @pytest.mark.asyncio
    async def test_real_milvus_check_rejects_lite_uri_without_connecting(self):
        cfg = DeepResearchConfig.model_validate({"milvus": {"uri": "./data/test.db"}})
        with patch("deepresearch.doctor.MilvusClient") as client_cls:
            check = await _check_milvus(cfg)

        client_cls.assert_not_called()
        assert not check.ok
        assert "local .db" in check.message

    @pytest.mark.asyncio
    async def test_real_langfuse_check_requires_keys(self, monkeypatch):
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        cfg = DeepResearchConfig.model_validate({"langfuse": {"enabled": True}})

        check = await _check_langfuse(cfg)

        assert not check.ok
        assert "LANGFUSE_PUBLIC_KEY" in check.message

    @pytest.mark.asyncio
    async def test_real_langfuse_check_auth_success(self, monkeypatch):
        from unittest.mock import MagicMock

        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
        mock_client = MagicMock()
        mock_client.auth_check.return_value = True
        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = "prompt"
        mock_client.get_prompt.return_value = mock_prompt
        mock_langfuse = MagicMock(return_value=mock_client)
        cfg = DeepResearchConfig.model_validate(
            {"langfuse": {"prompt_provider": "langfuse_with_local_fallback"}}
        )

        with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse)}):
            check = await _check_langfuse(cfg)

        assert check.ok
        assert "Langfuse endpoint OK" in check.message
        assert mock_client.get_prompt.call_count == 7
        mock_client.shutdown.assert_called_once()

    def test_langfuse_prompt_check_reports_missing_prompt(self):
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.get_prompt.side_effect = Exception("not found")
        cfg = DeepResearchConfig.model_validate(
            {
                "langfuse": {
                    "prompt_provider": "langfuse",
                    "prompt_label": "production",
                }
            }
        )

        check = _check_langfuse_prompts(mock_client, cfg)

        assert not check.ok
        assert check.name == "langfuse_prompts"
        assert "planner" in check.message
        assert "production" in check.message

    def test_real_checks_are_opt_in(self):
        with patch("deepresearch.doctor._real_checks") as real_checks:
            run_doctor(real=False)
        real_checks.assert_not_called()

    def test_real_checks_are_included_when_requested(self):
        async def fake_real_checks(_cfg):
            return [CheckResult(name="llm_endpoint", ok=True, message="ok")]

        with patch("deepresearch.doctor._real_checks") as real_checks:
            real_checks.side_effect = fake_real_checks
            report = run_doctor(real=True)

        assert any(c.name == "llm_endpoint" for c in report.checks)

    def test_env_check_respects_optional_llm_api_key(self, monkeypatch):
        cfg = DeepResearchConfig.model_validate(
            {
                "llm": {
                    "provider": "openai_compatible",
                    "api_key_env": "",
                    "api_key_required": False,
                }
            }
        )

        report = run_doctor(cfg)

        assert not any(c.name == "" for c in report.checks)
