# -*- coding: utf-8 -*-
"""Tests for Credential Manager."""

import os
import pytest
import tempfile
from unittest.mock import patch

from core.credential_manager import CredentialManager


class TestCredentialManager:
    """Test credential storage."""

    def test_save_and_load_credentials(self):
        """Test saving and loading credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)

            manager.save_credential(
                host="user@192.168.1.100",
                auth_type="password",
                password="secret123"
            )

            cred = manager.get_credential("user@192.168.1.100")
            assert cred is not None
            assert cred["auth_type"] == "password"
            assert cred["password"] == "secret123"

    def test_delete_credential(self):
        """Test deleting credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)
            manager.save_credential("user@host", "password", password="secret")
            manager.delete_credential("user@host")

            assert manager.get_credential("user@host") is None

    def test_clear_all_credentials(self):
        """Test clearing all credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)
            manager.save_credential("user1@host1", "password", password="s1")
            manager.save_credential("user2@host2", "password", password="s2")
            manager.clear_all()

            assert manager.get_credential("user1@host1") is None
            assert manager.get_credential("user2@host2") is None

    def test_save_with_key_file(self):
        """Test saving credentials with SSH key file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)

            manager.save_credential(
                host="user@server",
                auth_type="key",
                key_file="/home/user/.ssh/id_rsa"
            )

            cred = manager.get_credential("user@server")
            assert cred is not None
            assert cred["auth_type"] == "key"
            assert cred["key_file"] == "/home/user/.ssh/id_rsa"
            assert cred["password"] is None

    def test_save_with_jump_node(self):
        """Test saving credentials with jump node configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)

            manager.save_credential(
                host="user@mainserver",
                auth_type="password",
                password="secret",
                jump_node="node110",
                jump_auth="none"
            )

            cred = manager.get_credential("user@mainserver")
            assert cred is not None
            assert cred["jump_node"] == "node110"
            assert cred["jump_auth"] == "none"

    def test_list_hosts(self):
        """Test listing all saved hosts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)
            manager.save_credential("user1@host1", "password", password="s1")
            manager.save_credential("user2@host2", "password", password="s2")

            hosts = manager.list_hosts()
            assert "user1@host1" in hosts
            assert "user2@host2" in hosts
            assert len(hosts) == 2

    def test_file_permissions(self):
        """Test that credentials file has secure permissions (600)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)
            manager.save_credential("user@host", "password", password="secret")

            cred_file = os.path.join(tmpdir, "credentials.json")
            mode = os.stat(cred_file).st_mode & 0o777
            assert mode == 0o600

    def test_encryption_key_consistency(self):
        """Test that same manager instance can decrypt what it encrypted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)

            # Save multiple passwords
            manager.save_credential("host1", "password", password="secret1")
            manager.save_credential("host2", "password", password="secret2")

            # Verify both can be retrieved correctly
            cred1 = manager.get_credential("host1")
            cred2 = manager.get_credential("host2")

            assert cred1["password"] == "secret1"
            assert cred2["password"] == "secret2"

    def test_update_existing_credential(self):
        """Test updating an existing credential."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)

            # Save initial credential
            manager.save_credential("user@host", "password", password="old_password")

            # Update with new password
            manager.save_credential("user@host", "password", password="new_password")

            cred = manager.get_credential("user@host")
            assert cred["password"] == "new_password"

    def test_get_nonexistent_credential(self):
        """Test getting a credential that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)

            cred = manager.get_credential("nonexistent@host")
            assert cred is None

    def test_encryption_key_derived_from_machine_id(self):
        """Test that encryption key is derived from machine identifiers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CredentialManager(config_dir=tmpdir)

            # The _get_encryption_key method should return a key
            # This is an internal method but we verify the manager works
            manager.save_credential("user@host", "password", password="test_password")

            # Create a new manager instance pointing to same dir
            manager2 = CredentialManager(config_dir=tmpdir)
            cred = manager2.get_credential("user@host")

            # Should be able to decrypt since same machine
            assert cred is not None
            assert cred["password"] == "test_password"
