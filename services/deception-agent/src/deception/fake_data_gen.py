"""Realistic fabricated data generator for deception operations."""

import random
import uuid
import hashlib
import time
from datetime import datetime, timedelta


class FakeDataGenerator:
    """
    Generates realistic but fabricated data for shadow sessions.
    All generated data contains embedded canary tokens for tracking.
    """

    FIRST_NAMES = [
        "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
        "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
        "Joseph", "Jessica", "Thomas", "Sarah", "Christopher", "Karen",
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
        "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    ]

    DOMAINS = [
        "gmail.com", "yahoo.com", "outlook.com", "protonmail.com",
        "company.com", "enterprise.io", "corp.net",
    ]

    def __init__(self, canary_prefix: str = "CANARY"):
        self.canary_prefix = canary_prefix

    def generate_fake_users(self, count: int = 10) -> list[dict]:
        """Generate fake user profiles with embedded canary tokens."""
        users = []
        for _ in range(count):
            first = random.choice(self.FIRST_NAMES)
            last = random.choice(self.LAST_NAMES)
            domain = random.choice(self.DOMAINS)
            canary_id = uuid.uuid4().hex[:8]

            users.append({
                "id": f"usr-{uuid.uuid4().hex[:12]}",
                "email": f"{first.lower()}.{last.lower()}@{domain}",
                "name": f"{first} {last}",
                "role": random.choice(["user", "admin", "manager", "analyst"]),
                "created_at": self._random_date(),
                "last_login": self._random_recent_date(),
                "status": random.choice(["active", "active", "active", "suspended"]),
                # Canary token embedded in internal ID
                "_internal_id": f"{self.canary_prefix}-{canary_id}",
            })

        return users

    def generate_fake_transactions(self, count: int = 20) -> list[dict]:
        """Generate fake financial transactions."""
        transactions = []
        for _ in range(count):
            canary_id = uuid.uuid4().hex[:8]
            transactions.append({
                "id": f"txn-{uuid.uuid4().hex[:12]}",
                "amount": round(random.uniform(10.0, 9999.99), 2),
                "currency": random.choice(["USD", "EUR", "GBP"]),
                "type": random.choice(["credit", "debit", "transfer"]),
                "status": random.choice(["completed", "pending", "completed"]),
                "merchant": f"{random.choice(self.LAST_NAMES)} Corp",
                "card_last4": f"{random.randint(1000, 9999)}",
                "timestamp": self._random_recent_date(),
                "reference": f"{self.canary_prefix}-{canary_id}",
            })

        return transactions

    def generate_fake_api_keys(self, count: int = 5) -> list[dict]:
        """Generate fake API keys — all are canary tokens."""
        keys = []
        for i in range(count):
            canary_id = uuid.uuid4().hex
            keys.append({
                "id": f"key-{uuid.uuid4().hex[:8]}",
                "name": f"{'Production' if i == 0 else 'Development'} API Key",
                "key": f"civa_{'live' if i == 0 else 'test'}_{canary_id}",
                "created_at": self._random_date(),
                "last_used": self._random_recent_date(),
                "permissions": ["read", "write"] if i == 0 else ["read"],
                # This key triggers alert when used anywhere
                "_canary": True,
            })

        return keys

    def generate_fake_admin_records(self) -> dict:
        """Generate fake admin panel data."""
        return {
            "total_users": random.randint(10000, 50000),
            "active_sessions": random.randint(500, 2000),
            "revenue_mtd": round(random.uniform(100000, 500000), 2),
            "pending_tickets": random.randint(50, 200),
            "system_status": "operational",
            "recent_logins": self.generate_fake_users(5),
            "recent_transactions": self.generate_fake_transactions(5),
            "api_keys": self.generate_fake_api_keys(3),
        }

    def _random_date(self) -> str:
        """Generate a random date in the past year."""
        days_ago = random.randint(1, 365)
        dt = datetime.now() - timedelta(days=days_ago)
        return dt.isoformat()

    def _random_recent_date(self) -> str:
        """Generate a random date in the past 7 days."""
        hours_ago = random.randint(1, 168)
        dt = datetime.now() - timedelta(hours=hours_ago)
        return dt.isoformat()
