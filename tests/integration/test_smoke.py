import os

import pytest

from deepresearch.config import load_config
from deepresearch.doctor import run_doctor


def _real_integration_enabled() -> bool:
    return os.environ.get("DEEPRESEARCH_RUN_REAL_INTEGRATION") == "1"


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.llm
@pytest.mark.milvus
def test_real_doctor_smoke():
    if not _real_integration_enabled():
        pytest.skip("set DEEPRESEARCH_RUN_REAL_INTEGRATION=1 to run real smoke checks")

    report = run_doctor(load_config(), real=True)

    assert report.all_ok, "\n".join(c.message for c in report.errors)


@pytest.mark.integration
def test_config_loads_for_integration_profile():
    cfg = load_config()

    assert cfg.llm.provider
    assert cfg.embedding.model
    assert cfg.reranker.model
    assert cfg.milvus.uri
