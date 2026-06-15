from unittest.mock import MagicMock, patch

from deepresearch.memory.milvus_store import MilvusLiteStore


def test_connect_creates_expected_collections_and_fields():
    created_schemas = []

    def fake_collection(*, name, schema):
        created_schemas.append((name, schema))
        col = MagicMock()
        col.create_index = MagicMock()
        return col

    with (
        patch("deepresearch.memory.milvus_store.connections") as connections,
        patch("deepresearch.memory.milvus_store.utility") as utility,
        patch("deepresearch.memory.milvus_store.Collection", side_effect=fake_collection),
    ):
        utility.has_collection.return_value = False

        store = MilvusLiteStore(uri="./data/test.db")
        store.connect()

        connections.connect.assert_called_once_with(alias="default", uri="./data/test.db")

    assert [name for name, _ in created_schemas] == [
        "deepresearch_chunks",
        "deepresearch_memories",
    ]

    for _, schema in created_schemas:
        fields = {field.name: field for field in schema.fields}
        assert set(fields) == {
            "id",
            "run_id",
            "task_id",
            "title",
            "source_url",
            "content",
            "source_type",
            "confidence",
            "created_at",
            "metadata_json",
            "embedding",
        }
        assert fields["embedding"].params["dim"] == 1024


def test_connect_creates_hnsw_cosine_index():
    indexes = []

    def fake_collection(*, name, schema):
        col = MagicMock()

        def create_index(*, field_name, index_params):
            indexes.append((name, field_name, index_params))

        col.create_index.side_effect = create_index
        return col

    with (
        patch("deepresearch.memory.milvus_store.connections"),
        patch("deepresearch.memory.milvus_store.utility") as utility,
        patch("deepresearch.memory.milvus_store.Collection", side_effect=fake_collection),
    ):
        utility.has_collection.return_value = False
        MilvusLiteStore().connect()

    assert len(indexes) == 2
    for _, field_name, index_params in indexes:
        assert field_name == "embedding"
        assert index_params["index_type"] == "HNSW"
        assert index_params["metric_type"] == "COSINE"
