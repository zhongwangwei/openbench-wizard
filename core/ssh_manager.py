# -*- coding: utf-8 -*-
"""
SSH Manager for remote server connections.

Handles SSH connections, file transfers, and remote command execution.
"""

import os
import re
from typing import Optional, Tuple, List, Callable, Generator

import paramiko
from paramiko import SSHClient, AutoAddPolicy, RSAKey, SSHException


class SSHConnectionError(Exception):
    """SSH connection error."""
    pass


class SSHManager:
    """Manage SSH connections, file transfer, and remote command execution."""

    def __init__(self, timeout: int = 30):
        """Initialize SSH manager.

        Args:
            timeout: Connection timeout in seconds
        """
        self._client: Optional[SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._timeout = timeout
        self._host = ""
        self._user = ""
        self._port = 22

    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        if self._client is None:
            return False
        try:
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False

    def _parse_host_string(self, host_string: str) -> Tuple[Optional[str], str, int]:
        """Parse host string in format [user@]host[:port].

        Args:
            host_string: Host string like "user@192.168.1.100:22"

        Returns:
            Tuple of (user, host, port)
        """
        user = None
        port = 22

        # Extract user if present
        if "@" in host_string:
            user, host_string = host_string.split("@", 1)

        # Extract port if present
        if ":" in host_string:
            host, port_str = host_string.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                host = host_string
        else:
            host = host_string

        return user, host, port

    def connect(
        self,
        host_string: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        passphrase: Optional[str] = None
    ) -> None:
        """Connect to SSH server.

        Args:
            host_string: Host in format [user@]host[:port]
            password: Password for authentication
            key_file: Path to SSH private key file
            passphrase: Passphrase for encrypted key file

        Raises:
            SSHConnectionError: If connection fails
        """
        user, host, port = self._parse_host_string(host_string)

        if user is None:
            raise SSHConnectionError("Username is required (format: user@host)")

        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(AutoAddPolicy())

        try:
            self._client.connect(
                hostname=host,
                port=port,
                username=user,
                password=password,
                key_filename=key_file,
                timeout=self._timeout,
                allow_agent=False,
                look_for_keys=False
            )
            self._host = host
            self._user = user
            self._port = port
        except SSHException as e:
            self._client = None
            raise SSHConnectionError(f"SSH connection failed: {e}")
        except Exception as e:
            self._client = None
            raise SSHConnectionError(f"Connection failed: {e}")

    def disconnect(self) -> None:
        """Disconnect from server."""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def test_connection(self) -> bool:
        """Test if connection is alive.

        Returns:
            True if connected and responsive
        """
        if not self.is_connected:
            return False
        try:
            self._client.exec_command("echo ok", timeout=5)
            return True
        except Exception:
            return False

    def execute(self, command: str, timeout: Optional[int] = None) -> Tuple[str, str, int]:
        """Execute command on remote server.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (stdout, stderr, exit_code)

        Raises:
            SSHConnectionError: If not connected
        """
        if not self.is_connected:
            raise SSHConnectionError("Not connected to server")

        try:
            stdin, stdout, stderr = self._client.exec_command(
                command,
                timeout=timeout or self._timeout
            )
            exit_code = stdout.channel.recv_exit_status()
            return (
                stdout.read().decode('utf-8', errors='replace'),
                stderr.read().decode('utf-8', errors='replace'),
                exit_code
            )
        except SSHException as e:
            raise SSHConnectionError(f"Command execution failed: {e}")

    def execute_stream(
        self,
        command: str,
        callback: Optional[Callable[[str], None]] = None
    ) -> Generator[str, None, int]:
        """Execute command and stream output.

        Args:
            command: Command to execute
            callback: Optional callback for each line of output

        Yields:
            Lines of output

        Returns:
            Exit code
        """
        if not self.is_connected:
            raise SSHConnectionError("Not connected to server")

        transport = self._client.get_transport()
        channel = transport.open_session()
        channel.exec_command(command)

        # Read output in real-time
        while not channel.exit_status_ready() or channel.recv_ready():
            if channel.recv_ready():
                data = channel.recv(4096).decode('utf-8', errors='replace')
                for line in data.splitlines(keepends=True):
                    if callback:
                        callback(line)
                    yield line

        return channel.recv_exit_status()
