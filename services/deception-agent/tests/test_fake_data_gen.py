"""Unit tests for the FakeDataGenerator."""

import pytest
from src.deception.fake_data_gen import FakeDataGenerator


class TestFakeDataGenerator:
    """Tests for realistic canary-embedded fake data generation."""

    def test_init_default_prefix(self):
        gen = FakeDataGenerator()
        assert gen.canary_prefix == "CANARY"

    def test_init_custom_prefix(self):
        gen = FakeDataGenerator(canary_prefix="TRAP")
        assert gen.canary_prefix == "TRAP"

    def test_generate_fake_users_count(self, fake_data_gen):
        users = fake_data_gen.generate_fake_users(count=5)
        assert len(users) == 5

    def test_generate_fake_users_default_count(self, fake_data_gen):
        users = fake_data_gen.generate_fake_users()
        assert len(users) == 10

    def test_fake_users_have_required_fields(self, fake_data_gen):
        users = fake_data_gen.generate_fake_users(count=1)
        user = users[0]
        assert "id" in user
        assert "email" in user
        assert "name" in user
        assert "role" in user
        assert "created_at" in user
        assert "_internal_id" in user

    def test_fake_users_contain_canary_tokens(self, fake_data_gen):
        users = fake_data_gen.generate_fake_users(count=3)
        for user in users:
            assert user["_internal_id"].startswith("CANARY-")

    def test_fake_users_have_valid_emails(self, fake_data_gen):
        users = fake_data_gen.generate_fake_users(count=5)
        for user in users:
            assert "@" in user["email"]
            assert "." in user["email"]

    def test_fake_users_have_valid_roles(self, fake_data_gen):
        users = fake_data_gen.generate_fake_users(count=20)
        valid_roles = {"user", "admin", "manager", "analyst"}
        for user in users:
            assert user["role"] in valid_roles

    def test_generate_fake_transactions_count(self, fake_data_gen):
        txns = fake_data_gen.generate_fake_transactions(count=7)
        assert len(txns) == 7

    def test_fake_transactions_have_required_fields(self, fake_data_gen):
        txns = fake_data_gen.generate_fake_transactions(count=1)
        txn = txns[0]
        assert "id" in txn
        assert "amount" in txn
        assert "currency" in txn
        assert "type" in txn
        assert "reference" in txn

    def test_fake_transactions_contain_canary_tokens(self, fake_data_gen):
        txns = fake_data_gen.generate_fake_transactions(count=3)
        for txn in txns:
            assert txn["reference"].startswith("CANARY-")

    def test_fake_transactions_valid_amounts(self, fake_data_gen):
        txns = fake_data_gen.generate_fake_transactions(count=20)
        for txn in txns:
            assert 10.0 <= txn["amount"] <= 9999.99

    def test_generate_fake_api_keys(self, fake_data_gen):
        keys = fake_data_gen.generate_fake_api_keys(count=3)
        assert len(keys) == 3
        for key in keys:
            assert "_canary" in key
            assert key["_canary"] is True

    def test_fake_api_keys_contain_canary_in_value(self, fake_data_gen):
        keys = fake_data_gen.generate_fake_api_keys(count=2)
        for key in keys:
            assert "canary" in key["key"].lower() or "civa" in key["key"]

    def test_generate_fake_admin_records(self, fake_data_gen):
        admin = fake_data_gen.generate_fake_admin_records()
        assert "total_users" in admin
        assert "active_sessions" in admin
        assert "revenue_mtd" in admin
        assert "recent_logins" in admin
        assert "recent_transactions" in admin
        assert "api_keys" in admin
        assert admin["system_status"] == "operational"

    def test_admin_records_contain_nested_fakes(self, fake_data_gen):
        admin = fake_data_gen.generate_fake_admin_records()
        assert len(admin["recent_logins"]) == 5
        assert len(admin["recent_transactions"]) == 5
        assert len(admin["api_keys"]) == 3
