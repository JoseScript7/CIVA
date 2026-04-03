"""Honeypot endpoints — Trap endpoints that trigger immediate session termination.

Any request to these endpoints is conclusive evidence of malicious intent.
Normal users would never navigate to these paths.
"""

import time
import uuid
from fastapi import APIRouter, Request

import sys
sys.path.insert(0, "../../../shared/python")
from civa_common.logging import get_logger
from civa_common.kafka_utils import KafkaProducer

from src.core.config import settings
from src.deception.fake_data_gen import FakeDataGenerator

logger = get_logger(__name__)
honeypot_router = APIRouter(tags=["honeypots"])
fake_data = FakeDataGenerator()

producer = KafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    client_id="deception-honeypot",
)


def _log_honeypot_trigger(request: Request, endpoint: str) -> dict:
    """Log honeypot trigger and publish termination event."""
    event = {
        "event_type": "honeypot_triggered",
        "timestamp_us": int(time.time() * 1_000_000),
        "event_id": str(uuid.uuid4()),
        "endpoint": endpoint,
        "client_ip": request.client.host if request.client else "unknown",
        "method": request.method,
        "path": str(request.url.path),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
    }

    producer.produce(
        topic=settings.KAFKA_OUTPUT_TOPIC,
        value=event,
        headers={"event_type": "honeypot_trigger"},
    )

    logger.critical(
        "🍯 HONEYPOT TRIGGERED",
        endpoint=endpoint,
        client_ip=event["client_ip"],
        path=event["path"],
    )

    return event


@honeypot_router.get("/admin/export-all-users")
async def honeypot_export_users(request: Request):
    """Honeypot: Mass user data export — immediate kill trigger."""
    _log_honeypot_trigger(request, "export-all-users")
    # Return believable fake data before killing the session
    return {
        "status": "processing",
        "export_id": str(uuid.uuid4()),
        "estimated_records": 124_589,
        "message": "Export queued. Download link will be sent to admin email.",
    }


@honeypot_router.get("/admin/database-backup")
async def honeypot_db_backup(request: Request):
    """Honeypot: Database backup access."""
    _log_honeypot_trigger(request, "database-backup")
    return {
        "status": "ready",
        "backup_id": f"backup-{uuid.uuid4().hex[:8]}",
        "size_gb": 12.4,
        "download_url": f"https://{settings.CANARY_DOMAIN}/dl/{uuid.uuid4()}",
        "expires_in": 3600,
    }


@honeypot_router.get("/internal/config")
async def honeypot_internal_config(request: Request):
    """Honeypot: Internal configuration leak."""
    _log_honeypot_trigger(request, "internal-config")
    return {
        "database": {
            "host": f"rds-{uuid.uuid4().hex[:8]}.us-east-1.rds.amazonaws.com",
            "port": 5432,
            "user": "admin",
            "password": f"canary-{uuid.uuid4().hex[:12]}",
        },
        "api_keys": {
            "stripe": f"sk_live_canary_{uuid.uuid4().hex}",
            "sendgrid": f"SG.canary_{uuid.uuid4().hex}",
        },
        "aws": {
            "access_key": f"AKIA{uuid.uuid4().hex[:16].upper()}",
            "secret_key": f"canary/{uuid.uuid4().hex}",
        },
    }


@honeypot_router.get("/.env")
async def honeypot_env_file(request: Request):
    """Honeypot: Environment file access."""
    _log_honeypot_trigger(request, "env-file")
    return f"""# Production Environment
DATABASE_URL=postgresql://admin:canary-{uuid.uuid4().hex[:12]}@db.internal:5432/prod
SECRET_KEY={uuid.uuid4().hex}
AWS_ACCESS_KEY_ID=AKIA{uuid.uuid4().hex[:16].upper()}
AWS_SECRET_ACCESS_KEY=canary/{uuid.uuid4().hex}
STRIPE_SECRET_KEY=sk_live_canary_{uuid.uuid4().hex}
ADMIN_PASSWORD=canary-{uuid.uuid4().hex[:8]}
"""


@honeypot_router.get("/admin/impersonate/{user_id}")
async def honeypot_impersonate(request: Request, user_id: str):
    """Honeypot: User impersonation attempt."""
    _log_honeypot_trigger(request, "impersonate-user")
    return {
        "status": "impersonating",
        "target_user": user_id,
        "session_token": f"canary-session-{uuid.uuid4().hex}",
        "expires_in": 1800,
    }


@honeypot_router.get("/graphql/introspection")
async def honeypot_graphql(request: Request):
    """Honeypot: GraphQL schema introspection."""
    _log_honeypot_trigger(request, "graphql-introspection")
    return {
        "data": {
            "__schema": {
                "types": [
                    {"name": "User", "fields": ["id", "email", "password_hash", "ssn"]},
                    {"name": "Transaction", "fields": ["id", "amount", "card_number"]},
                    {"name": "AdminConfig", "fields": ["api_keys", "secrets"]},
                ],
            }
        }
    }


@honeypot_router.post("/debug/sql")
async def honeypot_sql(request: Request):
    """Honeypot: SQL injection bait."""
    _log_honeypot_trigger(request, "debug-sql")
    return {
        "status": "executed",
        "rows_affected": 0,
        "message": "Query executed successfully",
        "result": fake_data.generate_fake_users(5),
    }
