"""S3 Parquet forensic logger — Microsecond-precision attack logging."""

import json
import time
import uuid
import os
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

import sys
sys.path.insert(0, "../../../shared/python")
from civa_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ForensicLogEntry:
    """A single forensic log entry with microsecond precision."""
    timestamp_us: int
    session_id: str
    shadow_session_id: str
    attacker_ip: str
    request_method: str
    request_path: str
    request_headers: dict
    request_body: str
    response_code: int
    response_body: str
    canary_tokens_served: list[str]
    honeypot_triggered: bool
    geo_location: dict
    device_fingerprint: str
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return asdict(self)


class ForensicLogger:
    """
    Logs all attacker interactions to S3 in Parquet format.
    
    S3 Layout:
      s3://civa-forensics/
        └── year=YYYY/month=MM/day=DD/session_id=XXX/
            ├── events_00001.parquet
            └── summary.json
    
    For local development, logs to filesystem.
    """

    def __init__(self, bucket: str = "civa-forensics", local_path: str = "./forensic_logs"):
        self.bucket = bucket
        self.local_path = local_path
        self._buffer: dict[str, list[ForensicLogEntry]] = {}
        self._buffer_size = 100  # Flush to S3 every 100 entries

    def log(self, entry: ForensicLogEntry) -> None:
        """Buffer a forensic log entry."""
        key = entry.session_id
        if key not in self._buffer:
            self._buffer[key] = []

        self._buffer[key].append(entry)

        logger.debug(
            "Forensic log entry",
            session_id=entry.session_id,
            path=entry.request_path,
            honeypot=entry.honeypot_triggered,
        )

        # Auto-flush when buffer is full
        if len(self._buffer[key]) >= self._buffer_size:
            self.flush(entry.session_id)

    def flush(self, session_id: Optional[str] = None) -> None:
        """Flush buffered entries to storage."""
        sessions = [session_id] if session_id else list(self._buffer.keys())

        for sid in sessions:
            entries = self._buffer.get(sid, [])
            if not entries:
                continue

            # Build S3 path
            now = datetime.utcnow()
            path = (
                f"year={now.year}/month={now.month:02d}/day={now.day:02d}"
                f"/session_id={sid}"
            )

            # Write to local filesystem (S3 in production)
            local_dir = os.path.join(self.local_path, path)
            os.makedirs(local_dir, exist_ok=True)

            # Write entries as JSONL (Parquet in production)
            file_idx = len(os.listdir(local_dir)) + 1
            filepath = os.path.join(local_dir, f"events_{file_idx:05d}.jsonl")

            with open(filepath, "w") as f:
                for entry in entries:
                    f.write(json.dumps(entry.to_dict(), default=str) + "\n")

            logger.info(
                "Forensic logs flushed",
                session_id=sid,
                entries=len(entries),
                path=filepath,
            )

            # Clear buffer
            self._buffer[sid] = []

    def generate_summary(self, session_id: str) -> dict:
        """Generate a summary of all forensic data for a session."""
        entries = self._buffer.get(session_id, [])
        if not entries:
            return {"session_id": session_id, "total_events": 0}

        honeypot_triggers = [e for e in entries if e.honeypot_triggered]
        unique_paths = set(e.request_path for e in entries)
        canary_tokens = set()
        for e in entries:
            canary_tokens.update(e.canary_tokens_served)

        return {
            "session_id": session_id,
            "total_events": len(entries),
            "first_event_us": entries[0].timestamp_us,
            "last_event_us": entries[-1].timestamp_us,
            "duration_seconds": (entries[-1].timestamp_us - entries[0].timestamp_us) / 1_000_000,
            "unique_paths_accessed": len(unique_paths),
            "paths": list(unique_paths),
            "honeypot_triggers": len(honeypot_triggers),
            "canary_tokens_served": len(canary_tokens),
            "attacker_ip": entries[0].attacker_ip,
        }

    def flush_all(self) -> None:
        """Flush all buffered sessions."""
        for session_id in list(self._buffer.keys()):
            self.flush(session_id)
