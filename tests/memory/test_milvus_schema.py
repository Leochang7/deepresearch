from unittest.mock import MagicMock, patch

from deepresearch.memory.milvus_store import MilvusStore


def _make_mock_client():
    client = MagicMock()
    client.has_collection.return_value = False
    client.prepare_index_params.return_value = MagicMock()
    return client


def test_connect_creates_expected_collections():
    with patch("deepresearch.memory.milvus_store.MilvusClient") as mock_cls:
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        store = MilvusStore()
        store.connect()

        mock_cls.assert_called_once_with(uri="http://localhost:19530")
        assert mock_client.has_collection.call_count == 2
        assert mock_client.create_collection.call_count == 2
        assert mock_client.create_index.call_count == 2

        col_names = [
            call.kwargs["collection_name"]
            for call in mock_client.create_collection.call_args_list
        ]
        assert col_names == ["deepresearch_chunks", "deepresearch_memories"]


def test_connect_creates_hnsw_cosine_index():
    with patch("deepresearch.memory.milvus_store.MilvusClient") as mock_cls:
        mock_client = _make_mock_client()
        index_params = mock_client.prepare_index_params.return_value
        mock_cls.return_value = mock_client

        MilvusStore().connect()

        assert mock_client.prepare_index_params.call_count == 2
        assert index_params.add_index.call_count == 2
        for call in index_params.add_index.call_args_list:
            assert call.kwargs["field_name"] == "embedding"
            assert call.kwargs["index_type"] == "HNSW"
            assert call.kwargs["metric_type"] == "COSINE"

        for call in mock_client.create_index.call_args_list:
            assert call.kwargs["index_params"] is index_params
            assert "field_name" not in call.kwargs


def test_connect_uses_configured_dimension():
    with patch("deepresearch.memory.milvus_store.MilvusClient") as mock_cls:
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        MilvusStore(dim=2560).connect()

        for call in mock_client.create_collection.call_args_list:
            schema = call.kwargs["schema"]
            embedding_field = next(f for f in schema.fields if f.name == "embedding")
            assert embedding_field.params["dim"] == 2560


def test_close_disconnects_client():
    with patch("deepresearch.memory.milvus_store.MilvusClient") as mock_cls:
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        store = MilvusStore()
        store.connect()
        store.close()

        mock_client.close.assert_called_once()


def test_existing_collection_dimension_mismatch_fails_fast():
    with patch("deepresearch.memory.milvus_store.MilvusClient") as mock_cls:
        mock_client = _make_mock_client()
        mock_client.has_collection.return_value = True
        mock_client.describe_collection.return_value = {
            "fields": [
                {
                    "name": "embedding",
                    "params": {"dim": 1024},
                }
            ]
        }
        mock_cls.return_value = mock_client

        store = MilvusStore(dim=2560)

        try:
            store.connect()
        except ValueError as exc:
            assert "embedding dim mismatch" in str(exc)
        else:
            raise AssertionError("expected dimension mismatch to fail")
