# -*- coding: utf-8 -*-
"""Tests for SSH Manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.ssh_manager import SSHManager, SSHConnectionError


class TestSSHManagerConnection:
    """Test SSH connection functionality."""

    def test_parse_host_string_with_user(self):
        """Test parsing user@host format."""
        manager = SSHManager()
        user, host, port = manager._parse_host_string("user@192.168.1.100")
        assert user == "user"
        assert host == "192.168.1.100"
        assert port == 22

    def test_parse_host_string_with_port(self):
        """Test parsing user@host:port format."""
        manager = SSHManager()
        user, host, port = manager._parse_host_string("user@192.168.1.100:2222")
        assert user == "user"
        assert host == "192.168.1.100"
        assert port == 2222

    def test_parse_host_string_without_user(self):
        """Test parsing host only format."""
        manager = SSHManager()
        user, host, port = manager._parse_host_string("192.168.1.100")
        assert user is None
        assert host == "192.168.1.100"
        assert port == 22

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_connect_with_password(self, mock_ssh_class):
        """Test connection with password authentication."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        manager = SSHManager()
        manager.connect("user@192.168.1.100", password="secret")

        mock_client.connect.assert_called_once_with(
            hostname="192.168.1.100",
            port=22,
            username="user",
            password="secret",
            key_filename=None,
            timeout=30,
            allow_agent=False,
            look_for_keys=False
        )
        assert manager.is_connected

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_disconnect(self, mock_ssh_class):
        """Test disconnection."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        manager = SSHManager()
        manager.connect("user@192.168.1.100", password="secret")
        manager.disconnect()

        mock_client.close.assert_called_once()
        assert not manager.is_connected
