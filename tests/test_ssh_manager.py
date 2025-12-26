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


class TestSSHManagerExecution:
    """Test remote command execution."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_execute_command(self, mock_ssh_class):
        """Test executing a command."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        # Mock command execution
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout.read.return_value = b"hello\n"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        stdout, stderr, exit_code = manager.execute("echo hello")

        assert stdout == "hello\n"
        assert stderr == ""
        assert exit_code == 0

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_execute_stream(self, mock_ssh_class):
        """Test streaming command output."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        # Mock channel for streaming
        mock_channel = MagicMock()
        mock_channel.recv_ready.side_effect = [True, True, False]
        mock_channel.recv.side_effect = [b"line1\n", b"line2\n"]
        mock_channel.exit_status_ready.side_effect = [False, False, True]
        mock_channel.recv_exit_status.return_value = 0

        mock_transport = MagicMock()
        mock_transport.open_session.return_value = mock_channel
        mock_client.get_transport.return_value = mock_transport

        manager = SSHManager()
        manager.connect("user@host", password="secret")

        lines = list(manager.execute_stream("echo test"))
        assert "line1\n" in lines
        assert "line2\n" in lines
