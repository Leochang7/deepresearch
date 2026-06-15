import json

from deepresearch.core.trace import TraceEventType, TraceLogger


class TestTraceEventType:
    def test_all_event_types(self):
        expected = {
            "planner_created_plan",
            "task_state_changed",
            "retriever_called",
            "milvus_upserted",
            "milvus_searched",
            "llm_called",
            "red_review_created",
            "blue_fix_applied",
            "evaluation_completed",
        }
        actual = {e.value for e in TraceEventType}
        assert actual == expected


class TestTraceLogger:
    def test_log_creates_file(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        logger = TraceLogger(log_path)
        logger.log(
            TraceEventType.TASK_STATE_CHANGED,
            {"from_state": "READY", "to_state": "RUNNING"},
            task_id="t1",
        )
        assert log_path.exists()

    def test_log_writes_jsonl(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        logger = TraceLogger(log_path)
        logger.log(
            TraceEventType.TASK_STATE_CHANGED,
            {"from_state": "READY", "to_state": "RUNNING"},
            task_id="t1",
        )
        logger.log(TraceEventType.LLM_CALLED, {"model": "mimo", "tokens": 100})

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        event1 = json.loads(lines[0])
        assert event1["event_type"] == "task_state_changed"
        assert event1["metadata"]["from_state"] == "READY"
        assert event1["task_id"] == "t1"

        event2 = json.loads(lines[1])
        assert event2["event_type"] == "llm_called"
        assert event2["metadata"]["model"] == "mimo"

    def test_log_includes_run_id(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        logger = TraceLogger(log_path, run_id="run-123")
        logger.log(TraceEventType.TASK_STATE_CHANGED, {"status": "started"})

        event = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert event["run_id"] == "run-123"

    def test_log_includes_task_id(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        logger = TraceLogger(log_path)
        logger.log(
            TraceEventType.TASK_STATE_CHANGED,
            {"status": "started"},
            task_id="t1",
        )

        event = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert event["task_id"] == "t1"

    def test_log_includes_timestamp(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        logger = TraceLogger(log_path)
        logger.log(TraceEventType.TASK_STATE_CHANGED, {"status": "started"})

        event = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert "timestamp" in event
        # ISO format check
        assert "T" in event["timestamp"]

    def test_appends_across_calls(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        logger = TraceLogger(log_path)
        for i in range(5):
            logger.log(TraceEventType.TASK_STATE_CHANGED, {"i": i})

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 5

    def test_all_event_types_write(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        logger = TraceLogger(log_path, run_id="r1")

        for event_type in TraceEventType:
            logger.log(event_type, {"type": event_type.value})

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == len(TraceEventType)
        for i, event_type in enumerate(TraceEventType):
            event = json.loads(lines[i])
            assert event["event_type"] == event_type.value

    def test_context_manager(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        with TraceLogger(log_path, run_id="r1") as logger:
            logger.log(TraceEventType.TASK_STATE_CHANGED, {"status": "started"})
            logger.log(TraceEventType.LLM_CALLED, {"model": "mimo"})

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_retriever_event(self, tmp_path):
        log_path = tmp_path / "trace.jsonl"
        logger = TraceLogger(log_path)
        logger.log(
            TraceEventType.RETRIEVER_CALLED,
            {
                "retriever": "tavily",
                "query": "LLM agents",
                "result_count": 5,
                "duration_ms": 320,
            },
            task_id="t1",
        )

        event = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert event["event_type"] == "retriever_called"
        assert event["metadata"]["retriever"] == "tavily"
        assert event["task_id"] == "t1"
