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


class TestSSHManagerFileTransfer:
    """Test file transfer functionality."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_upload_file(self, mock_ssh_class):
        """Test uploading a file."""
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp
        mock_ssh_class.return_value = mock_client

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        manager.upload_file("/local/file.txt", "/remote/file.txt")

        mock_sftp.put.assert_called_once_with("/local/file.txt", "/remote/file.txt")

    @patch('core.ssh_manager.os.makedirs')
    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_download_file(self, mock_ssh_class, mock_makedirs):
        """Test downloading a file."""
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp
        mock_ssh_class.return_value = mock_client

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        manager.download_file("/remote/file.txt", "/local/file.txt")

        mock_sftp.get.assert_called_once_with("/remote/file.txt", "/local/file.txt")
        mock_makedirs.assert_called_once_with("/local", exist_ok=True)


class TestSSHManagerEnvironment:
    """Test environment detection."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_detect_python_interpreters(self, mock_ssh_class):
        """Test detecting Python interpreters."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        # Mock command responses
        def exec_side_effect(cmd, timeout=None):
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""
            mock_stdout.channel.recv_exit_status.return_value = 0

            if "echo $HOME" in cmd:
                mock_stdout.read.return_value = b"/home/user\n"
            elif "which python3" in cmd:
                mock_stdout.read.return_value = b"/usr/bin/python3\n"
            elif "which python" in cmd and "python3" not in cmd:
                mock_stdout.read.return_value = b"/usr/bin/python\n"
            elif "miniforge3" in cmd:
                mock_stdout.read.return_value = b"/home/user/miniforge3/bin/python\n"
            else:
                mock_stdout.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 1

            return mock_stdin, mock_stdout, mock_stderr

        mock_client.exec_command.side_effect = exec_side_effect

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        pythons = manager.detect_python_interpreters()

        assert "/usr/bin/python3" in pythons or len(pythons) > 0

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_detect_python_interpreters_multiple(self, mock_ssh_class):
        """Test detecting multiple Python interpreters."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        # Mock to return different pythons for different commands
        call_count = [0]

        def exec_side_effect(cmd, timeout=None):
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""

            if "echo $HOME" in cmd:
                mock_stdout.read.return_value = b"/home/user\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "which python3" in cmd:
                mock_stdout.read.return_value = b"/usr/bin/python3\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "which python" in cmd and "python3" not in cmd:
                mock_stdout.read.return_value = b"/usr/bin/python\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            else:
                mock_stdout.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 1

            return mock_stdin, mock_stdout, mock_stderr

        mock_client.exec_command.side_effect = exec_side_effect

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        pythons = manager.detect_python_interpreters()

        # Should find at least python3 and python
        assert len(pythons) >= 2
        assert "/usr/bin/python3" in pythons
        assert "/usr/bin/python" in pythons

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_detect_conda_envs(self, mock_ssh_class):
        """Test detecting conda environments."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        def exec_side_effect(cmd, timeout=None):
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""

            if "echo $HOME" in cmd:
                mock_stdout.read.return_value = b"/home/user\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "test -f /home/user/miniforge3/bin/conda" in cmd:
                mock_stdout.read.return_value = b"exists\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "conda env list" in cmd:
                mock_stdout.read.return_value = b"""# conda environments:
#
base                  *  /home/user/miniforge3
openbench                /home/user/miniforge3/envs/openbench
test_env                 /home/user/miniforge3/envs/test_env
"""
                mock_stdout.channel.recv_exit_status.return_value = 0
            else:
                mock_stdout.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 1

            return mock_stdin, mock_stdout, mock_stderr

        mock_client.exec_command.side_effect = exec_side_effect

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        envs = manager.detect_conda_envs()

        # Should find base, openbench, and test_env
        assert len(envs) == 3
        env_names = [e[0] for e in envs]
        assert "base" in env_names
        assert "openbench" in env_names
        assert "test_env" in env_names

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_detect_conda_envs_no_conda(self, mock_ssh_class):
        """Test detecting conda environments when conda is not installed."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        def exec_side_effect(cmd, timeout=None):
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""

            if "echo $HOME" in cmd:
                mock_stdout.read.return_value = b"/home/user\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            else:
                # No conda found
                mock_stdout.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 1

            return mock_stdin, mock_stdout, mock_stderr

        mock_client.exec_command.side_effect = exec_side_effect

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        envs = manager.detect_conda_envs()

        # Should return empty list when no conda
        assert len(envs) == 0

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_check_openbench_installed_true(self, mock_ssh_class):
        """Test checking OpenBench installation when it exists."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        def exec_side_effect(cmd, timeout=None):
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""

            if "test -f /home/user/OpenBench/openbench/openbench.py" in cmd:
                mock_stdout.read.return_value = b"exists\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            else:
                mock_stdout.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 1

            return mock_stdin, mock_stdout, mock_stderr

        mock_client.exec_command.side_effect = exec_side_effect

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        result = manager.check_openbench_installed("/home/user/OpenBench")

        assert result is True

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_check_openbench_installed_false(self, mock_ssh_class):
        """Test checking OpenBench installation when it doesn't exist."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        def exec_side_effect(cmd, timeout=None):
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""
            mock_stdout.read.return_value = b""
            mock_stdout.channel.recv_exit_status.return_value = 1

            return mock_stdin, mock_stdout, mock_stderr

        mock_client.exec_command.side_effect = exec_side_effect

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        result = manager.check_openbench_installed("/nonexistent/path")

        assert result is False

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_get_home_dir(self, mock_ssh_class):
        """Test getting remote home directory."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client

        def exec_side_effect(cmd, timeout=None):
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""

            if "echo $HOME" in cmd:
                mock_stdout.read.return_value = b"/home/testuser\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            else:
                mock_stdout.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 1

            return mock_stdin, mock_stdout, mock_stderr

        mock_client.exec_command.side_effect = exec_side_effect

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        home = manager._get_home_dir()

        assert home == "/home/testuser"


class TestSSHManagerJump:
    """Test multi-hop SSH connection."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_connect_with_jump(self, mock_ssh_class):
        """Test connection through jump server."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        # First call returns main client, second returns jump client
        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")
        manager.connect_with_jump("node110")

        mock_transport.open_channel.assert_called_once()
        assert manager.is_jump_connected

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_connect_with_jump_password(self, mock_ssh_class):
        """Test jump connection with password authentication."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")
        manager.connect_with_jump("node110", main_password="node_secret")

        # Verify jump client was connected with password
        mock_jump_client.connect.assert_called_once()
        call_kwargs = mock_jump_client.connect.call_args[1]
        assert call_kwargs['password'] == "node_secret"
        assert call_kwargs['sock'] == mock_channel

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_connect_with_jump_key_file(self, mock_ssh_class):
        """Test jump connection with SSH key authentication."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")
        manager.connect_with_jump("node110", main_key_file="/path/to/key")

        # Verify jump client was connected with key file
        mock_jump_client.connect.assert_called_once()
        call_kwargs = mock_jump_client.connect.call_args[1]
        assert call_kwargs['key_filename'] == "/path/to/key"

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_connect_with_jump_internal_trust(self, mock_ssh_class):
        """Test jump connection with internal trust (no auth needed)."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")
        # No password or key - internal trust
        manager.connect_with_jump("node110")

        # Verify jump client was connected with agent/keys enabled
        mock_jump_client.connect.assert_called_once()
        call_kwargs = mock_jump_client.connect.call_args[1]
        assert call_kwargs['allow_agent'] is True
        assert call_kwargs['look_for_keys'] is True

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_disconnect_jump(self, mock_ssh_class):
        """Test disconnecting from jump server."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")
        manager.connect_with_jump("node110")

        manager.disconnect_jump()

        mock_jump_client.close.assert_called_once()
        mock_channel.close.assert_called_once()
        assert not manager.is_jump_connected
        # Main connection should still be active
        assert manager.is_connected

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_connect_with_jump_requires_main_connection(self, mock_ssh_class):
        """Test that jump connection requires main connection first."""
        manager = SSHManager()

        with pytest.raises(SSHConnectionError) as exc_info:
            manager.connect_with_jump("node110")

        assert "Must connect to main server first" in str(exc_info.value)

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_get_active_client_returns_jump_when_connected(self, mock_ssh_class):
        """Test get_active_client returns jump client when connected."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")

        # Before jump connection, should return main client
        assert manager.get_active_client() == mock_main_client

        manager.connect_with_jump("node110")

        # After jump connection, should return jump client
        assert manager.get_active_client() == mock_jump_client

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_execute_uses_active_client(self, mock_ssh_class):
        """Test execute uses the active client (jump or main)."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        # Mock exec_command for jump client
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout.read.return_value = b"output\n"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_jump_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")
        manager.connect_with_jump("node110")

        stdout, stderr, exit_code = manager.execute("echo test")

        # Should use jump client for execution
        mock_jump_client.exec_command.assert_called_once()
        assert stdout == "output\n"

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_full_disconnect_cleans_up_both(self, mock_ssh_class):
        """Test disconnect cleans up both main and jump connections."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")
        manager.connect_with_jump("node110")

        manager.disconnect()

        mock_jump_client.close.assert_called_once()
        mock_channel.close.assert_called_once()
        mock_main_client.close.assert_called_once()
        assert not manager.is_connected
        assert not manager.is_jump_connected
