"""Unit tests for the Forensic Logger."""

import os
import json
import time
import pytest
from src.logging.s3_logger import ForensicLogger, ForensicLogEntry


def _make_entry(session_id="sess-001", path="/api/test", honeypot=False, **kwargs):
    """Helper to create a ForensicLogEntry."""
    return ForensicLogEntry(
        timestamp_us=int(time.time() * 1_000_000),
        session_id=session_id,
        shadow_session_id=f"shadow-{session_id}",
        attacker_ip=kwargs.get("attacker_ip", "10.0.0.1"),
        request_method="GET",
        request_path=path,
        request_headers={"User-Agent": "curl/7.84.0"},
        request_body="",
        response_code=200,
        response_body='{"ok": true}',
        canary_tokens_served=kwargs.get("canary_tokens", []),
        honeypot_triggered=honeypot,
        geo_location={"country": "US", "city": "NY"},
        device_fingerprint="fp-attacker-001",
    )


class TestForensicLogEntry:
    """Tests for ForensicLogEntry dataclass."""

    def test_auto_generates_event_id(self):
        entry = _make_entry()
        assert entry.event_id != ""
        assert len(entry.event_id) > 0

    def test_to_dict(self):
        entry = _make_entry()
        d = entry.to_dict()
        assert d["session_id"] == "sess-001"
        assert d["request_path"] == "/api/test"
        assert isinstance(d, dict)


class TestForensicLogger:
    """Tests for ForensicLogger buffering, flushing, and summaries."""

    def test_log_adds_to_buffer(self, forensic_logger):
        entry = _make_entry()
        forensic_logger.log(entry)
        assert len(forensic_logger._buffer["sess-001"]) == 1

    def test_log_multiple_entries(self, forensic_logger):
        for i in range(5):
            forensic_logger.log(_make_entry(path=f"/api/path-{i}"))
        assert len(forensic_logger._buffer["sess-001"]) == 5

    def test_log_separate_sessions(self, forensic_logger):
        forensic_logger.log(_make_entry(session_id="sess-A"))
        forensic_logger.log(_make_entry(session_id="sess-B"))
        assert "sess-A" in forensic_logger._buffer
        assert "sess-B" in forensic_logger._buffer

    def test_flush_writes_to_disk(self, forensic_logger):
        forensic_logger.log(_make_entry())
        forensic_logger.flush("sess-001")
        # Buffer should be cleared
        assert len(forensic_logger._buffer.get("sess-001", [])) == 0

    def test_flush_creates_jsonl_file(self, forensic_logger):
        forensic_logger.log(_make_entry())
        forensic_logger.log(_make_entry(path="/api/other"))
        forensic_logger.flush("sess-001")
        # Should have created files in the local_path
        found_jsonl = False
        for root, dirs, files in os.walk(forensic_logger.local_path):
            for f in files:
                if f.endswith(".jsonl"):
                    found_jsonl = True
                    filepath = os.path.join(root, f)
                    with open(filepath) as fh:
                        lines = fh.readlines()
                    assert len(lines) == 2
        assert found_jsonl

    def test_flush_all(self, forensic_logger):
        forensic_logger.log(_make_entry(session_id="sess-A"))
        forensic_logger.log(_make_entry(session_id="sess-B"))
        forensic_logger.flush_all()
        assert len(forensic_logger._buffer.get("sess-A", [])) == 0
        assert len(forensic_logger._buffer.get("sess-B", [])) == 0

    def test_auto_flush_on_buffer_full(self, forensic_logger):
        forensic_logger._buffer_size = 5
        for i in range(5):
            forensic_logger.log(_make_entry(path=f"/api/{i}"))
        # Buffer should have been auto-flushed
        assert len(forensic_logger._buffer.get("sess-001", [])) == 0

    def test_generate_summary_empty(self, forensic_logger):
        summary = forensic_logger.generate_summary("nonexistent")
        assert summary["total_events"] == 0

    def test_generate_summary_with_data(self, forensic_logger):
        forensic_logger.log(_make_entry(path="/api/users"))
        forensic_logger.log(_make_entry(path="/api/admin", honeypot=True))
        forensic_logger.log(_make_entry(
            path="/api/keys",
            canary_tokens=["canary-token-001"],
        ))
        summary = forensic_logger.generate_summary("sess-001")
        assert summary["total_events"] == 3
        assert summary["honeypot_triggers"] == 1
        assert summary["unique_paths_accessed"] == 3
        assert summary["attacker_ip"] == "10.0.0.1"
