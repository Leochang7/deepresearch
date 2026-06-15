import deepresearch
import deepresearch.agents
import deepresearch.core
import deepresearch.embeddings
import deepresearch.evaluation
import deepresearch.llm
import deepresearch.memory
import deepresearch.rerankers
import deepresearch.retrieval
import deepresearch.schemas


def test_all_packages_importable():
    """All subpackages should be importable."""
    assert hasattr(deepresearch, "__path__")
    assert hasattr(deepresearch.agents, "__path__")
    assert hasattr(deepresearch.core, "__path__")
    assert hasattr(deepresearch.memory, "__path__")
    assert hasattr(deepresearch.retrieval, "__path__")
    assert hasattr(deepresearch.llm, "__path__")
    assert hasattr(deepresearch.embeddings, "__path__")
    assert hasattr(deepresearch.rerankers, "__path__")
    assert hasattr(deepresearch.evaluation, "__path__")
    assert hasattr(deepresearch.schemas, "__path__")
