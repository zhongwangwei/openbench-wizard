# Remote Execution Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add SSH-based remote server execution capability to OpenBench Wizard

**Architecture:** Use paramiko for SSH connections, separate Wizard config (.wizard.yaml) from OpenBench config, extend existing EvaluationRunner pattern for remote execution

**Tech Stack:** paramiko (SSH), cryptography (password encryption), PySide6 (UI)

---

## Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Add new dependencies**

Edit `requirements.txt`:
```
PySide6>=6.5.0
PyYAML>=6.0
psutil>=5.9.0
paramiko>=3.0.0
cryptography>=41.0.0
```

**Step 2: Install dependencies**

Run: `pip install paramiko cryptography`
Expected: Successfully installed

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add paramiko and cryptography dependencies for remote execution"
```

---

## Task 2: Create SSH Manager - Basic Connection

**Files:**
- Create: `core/ssh_manager.py`
- Create: `tests/test_ssh_manager.py`

**Step 1: Create test file with basic connection test**

Create `tests/test_ssh_manager.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ssh_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core.ssh_manager'"

**Step 3: Create SSH Manager with basic connection**

Create `core/ssh_manager.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ssh_manager.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/ssh_manager.py tests/test_ssh_manager.py
git commit -m "feat: add SSH Manager with basic connection support"
```

---

## Task 3: SSH Manager - Command Execution

**Files:**
- Modify: `core/ssh_manager.py`
- Modify: `tests/test_ssh_manager.py`

**Step 1: Add command execution tests**

Add to `tests/test_ssh_manager.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ssh_manager.py::TestSSHManagerExecution -v`
Expected: FAIL with "AttributeError: 'SSHManager' object has no attribute 'execute'"

**Step 3: Implement command execution methods**

Add to `core/ssh_manager.py` in SSHManager class:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ssh_manager.py::TestSSHManagerExecution -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/ssh_manager.py tests/test_ssh_manager.py
git commit -m "feat: add command execution to SSH Manager"
```

---

## Task 4: SSH Manager - File Transfer

**Files:**
- Modify: `core/ssh_manager.py`
- Modify: `tests/test_ssh_manager.py`

**Step 1: Add file transfer tests**

Add to `tests/test_ssh_manager.py`:
```python
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

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_download_file(self, mock_ssh_class):
        """Test downloading a file."""
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp
        mock_ssh_class.return_value = mock_client

        manager = SSHManager()
        manager.connect("user@host", password="secret")
        manager.download_file("/remote/file.txt", "/local/file.txt")

        mock_sftp.get.assert_called_once_with("/remote/file.txt", "/local/file.txt")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ssh_manager.py::TestSSHManagerFileTransfer -v`
Expected: FAIL

**Step 3: Implement file transfer methods**

Add to `core/ssh_manager.py`:
```python
    def _get_sftp(self) -> paramiko.SFTPClient:
        """Get or create SFTP client.

        Returns:
            SFTP client

        Raises:
            SSHConnectionError: If not connected
        """
        if not self.is_connected:
            raise SSHConnectionError("Not connected to server")

        if self._sftp is None:
            self._sftp = self._client.open_sftp()
        return self._sftp

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file to remote server.

        Args:
            local_path: Local file path
            remote_path: Remote destination path
        """
        sftp = self._get_sftp()
        # Ensure remote directory exists
        remote_dir = os.path.dirname(remote_path)
        if remote_dir:
            self._ensure_remote_dir(remote_dir)
        sftp.put(local_path, remote_path)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from remote server.

        Args:
            remote_path: Remote file path
            local_path: Local destination path
        """
        sftp = self._get_sftp()
        # Ensure local directory exists
        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        sftp.get(remote_path, local_path)

    def upload_directory(self, local_dir: str, remote_dir: str) -> None:
        """Upload a directory recursively.

        Args:
            local_dir: Local directory path
            remote_dir: Remote destination path
        """
        sftp = self._get_sftp()
        self._ensure_remote_dir(remote_dir)

        for root, dirs, files in os.walk(local_dir):
            rel_path = os.path.relpath(root, local_dir)
            if rel_path == ".":
                remote_root = remote_dir
            else:
                remote_root = os.path.join(remote_dir, rel_path).replace("\\", "/")
                self._ensure_remote_dir(remote_root)

            for file in files:
                local_file = os.path.join(root, file)
                remote_file = os.path.join(remote_root, file).replace("\\", "/")
                sftp.put(local_file, remote_file)

    def _ensure_remote_dir(self, remote_dir: str) -> None:
        """Ensure remote directory exists.

        Args:
            remote_dir: Remote directory path
        """
        sftp = self._get_sftp()
        dirs = remote_dir.replace("\\", "/").split("/")
        path = ""
        for d in dirs:
            if not d:
                continue
            path = f"{path}/{d}"
            try:
                sftp.stat(path)
            except FileNotFoundError:
                sftp.mkdir(path)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ssh_manager.py::TestSSHManagerFileTransfer -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/ssh_manager.py tests/test_ssh_manager.py
git commit -m "feat: add file transfer to SSH Manager"
```

---

## Task 5: SSH Manager - Environment Detection

**Files:**
- Modify: `core/ssh_manager.py`
- Modify: `tests/test_ssh_manager.py`

**Step 1: Add environment detection tests**

Add to `tests/test_ssh_manager.py`:
```python
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

            if "which python3" in cmd:
                mock_stdout.read.return_value = b"/usr/bin/python3\n"
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ssh_manager.py::TestSSHManagerEnvironment -v`
Expected: FAIL

**Step 3: Implement environment detection**

Add to `core/ssh_manager.py`:
```python
    def detect_python_interpreters(self) -> List[str]:
        """Detect available Python interpreters on remote server.

        Returns:
            List of Python interpreter paths
        """
        pythons = []
        home = self._get_home_dir()

        # Check common locations
        paths_to_check = [
            "which python3",
            "which python",
            f"ls {home}/miniforge3/bin/python 2>/dev/null",
            f"ls {home}/miniconda3/bin/python 2>/dev/null",
            f"ls {home}/anaconda3/bin/python 2>/dev/null",
            "ls /opt/homebrew/bin/python3 2>/dev/null",
            "ls /usr/local/bin/python3 2>/dev/null",
        ]

        for cmd in paths_to_check:
            try:
                stdout, _, exit_code = self.execute(cmd, timeout=5)
                if exit_code == 0 and stdout.strip():
                    path = stdout.strip().split('\n')[0]
                    if path and path not in pythons:
                        pythons.append(path)
            except Exception:
                continue

        return pythons

    def detect_conda_envs(self) -> List[Tuple[str, str]]:
        """Detect conda environments on remote server.

        Returns:
            List of (env_name, env_path) tuples
        """
        envs = []
        home = self._get_home_dir()

        # Find conda executable
        conda_paths = [
            f"{home}/miniforge3/bin/conda",
            f"{home}/miniconda3/bin/conda",
            f"{home}/anaconda3/bin/conda",
        ]

        conda_exe = None
        for path in conda_paths:
            stdout, _, exit_code = self.execute(f"test -f {path} && echo exists", timeout=5)
            if exit_code == 0 and "exists" in stdout:
                conda_exe = path
                break

        if not conda_exe:
            return envs

        # Get environment list
        try:
            stdout, _, exit_code = self.execute(f"{conda_exe} env list", timeout=10)
            if exit_code == 0:
                for line in stdout.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 1:
                            name = parts[0].replace('*', '').strip()
                            path = parts[-1] if len(parts) > 1 else ""
                            if name and name != "base":
                                envs.append((name, path))
                            elif name == "base":
                                envs.insert(0, (name, path))
        except Exception:
            pass

        return envs

    def check_openbench_installed(self, path: str) -> bool:
        """Check if OpenBench is installed at given path.

        Args:
            path: Path to check

        Returns:
            True if OpenBench is installed
        """
        check_file = f"{path}/openbench/openbench.py"
        stdout, _, exit_code = self.execute(f"test -f {check_file} && echo exists", timeout=5)
        return exit_code == 0 and "exists" in stdout

    def _get_home_dir(self) -> str:
        """Get remote home directory.

        Returns:
            Home directory path
        """
        stdout, _, _ = self.execute("echo $HOME", timeout=5)
        return stdout.strip() or f"/home/{self._user}"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ssh_manager.py::TestSSHManagerEnvironment -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/ssh_manager.py tests/test_ssh_manager.py
git commit -m "feat: add environment detection to SSH Manager"
```

---

## Task 6: SSH Manager - Multi-hop Connection

**Files:**
- Modify: `core/ssh_manager.py`
- Modify: `tests/test_ssh_manager.py`

**Step 1: Add multi-hop connection test**

Add to `tests/test_ssh_manager.py`:
```python
class TestSSHManagerJump:
    """Test multi-hop SSH connection."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_connect_with_jump(self, mock_ssh_class):
        """Test connection through jump server."""
        mock_main_client = MagicMock()
        mock_jump_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
        mock_main_client.get_transport.return_value = mock_transport
        mock_transport.open_channel.return_value = mock_channel

        manager = SSHManager()
        manager.connect("user@mainserver", password="secret")
        manager.connect_jump("node110")

        mock_transport.open_channel.assert_called_once()
        assert manager.is_jump_connected
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ssh_manager.py::TestSSHManagerJump -v`
Expected: FAIL

**Step 3: Implement multi-hop connection**

Add to `core/ssh_manager.py`:
```python
    def __init__(self, timeout: int = 30):
        # ... existing init code ...
        self._jump_client: Optional[SSHClient] = None
        self._jump_channel = None

    @property
    def is_jump_connected(self) -> bool:
        """Check if connected to jump/compute node."""
        if self._jump_client is None:
            return False
        try:
            transport = self._jump_client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False

    def connect_jump(
        self,
        node: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None
    ) -> None:
        """Connect to compute node through main server.

        Args:
            node: Node name or address (e.g., "node110")
            password: Password if required (None for internal trust)
            key_file: SSH key file if required

        Raises:
            SSHConnectionError: If connection fails
        """
        if not self.is_connected:
            raise SSHConnectionError("Must connect to main server first")

        try:
            # Open channel to node through main server
            transport = self._client.get_transport()
            dest_addr = (node, 22)
            local_addr = ('127.0.0.1', 0)
            self._jump_channel = transport.open_channel(
                "direct-tcpip", dest_addr, local_addr
            )

            # Connect through the channel
            self._jump_client = paramiko.SSHClient()
            self._jump_client.set_missing_host_key_policy(AutoAddPolicy())

            if password:
                self._jump_client.connect(
                    hostname=node,
                    username=self._user,
                    password=password,
                    sock=self._jump_channel,
                    timeout=self._timeout,
                    allow_agent=False,
                    look_for_keys=False
                )
            elif key_file:
                self._jump_client.connect(
                    hostname=node,
                    username=self._user,
                    key_filename=key_file,
                    sock=self._jump_channel,
                    timeout=self._timeout
                )
            else:
                # Internal trust - try without auth
                self._jump_client.connect(
                    hostname=node,
                    username=self._user,
                    sock=self._jump_channel,
                    timeout=self._timeout,
                    allow_agent=True,
                    look_for_keys=True
                )
        except Exception as e:
            self._jump_client = None
            self._jump_channel = None
            raise SSHConnectionError(f"Jump connection failed: {e}")

    def disconnect_jump(self) -> None:
        """Disconnect from compute node."""
        if self._jump_client:
            try:
                self._jump_client.close()
            except Exception:
                pass
            self._jump_client = None

        if self._jump_channel:
            try:
                self._jump_channel.close()
            except Exception:
                pass
            self._jump_channel = None

    def get_active_client(self) -> SSHClient:
        """Get the active SSH client (jump or main).

        Returns:
            Active SSH client
        """
        if self.is_jump_connected:
            return self._jump_client
        return self._client
```

**Step 4: Update execute methods to use active client**

Modify `execute` and `execute_stream` to use `get_active_client()`:
```python
    def execute(self, command: str, timeout: Optional[int] = None) -> Tuple[str, str, int]:
        client = self.get_active_client()
        if client is None:
            raise SSHConnectionError("Not connected to server")
        # ... rest of implementation using client instead of self._client
```

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_ssh_manager.py::TestSSHManagerJump -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add core/ssh_manager.py tests/test_ssh_manager.py
git commit -m "feat: add multi-hop SSH connection support"
```

---

## Task 7: Credential Manager

**Files:**
- Create: `core/credential_manager.py`
- Create: `tests/test_credential_manager.py`

**Step 1: Create test file**

Create `tests/test_credential_manager.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_credential_manager.py -v`
Expected: FAIL

**Step 3: Implement Credential Manager**

Create `core/credential_manager.py`:
```python
# -*- coding: utf-8 -*-
"""
Credential Manager for secure password storage.

Stores SSH credentials with encryption.
"""

import os
import json
import hashlib
import getpass
from typing import Optional, Dict, Any
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class CredentialManager:
    """Manage encrypted credential storage."""

    CREDENTIALS_FILE = "credentials.json"

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize credential manager.

        Args:
            config_dir: Config directory path (default: ~/.openbench_wizard)
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".openbench_wizard")
        self._config_dir = config_dir
        self._credentials_path = os.path.join(config_dir, self.CREDENTIALS_FILE)
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """Create Fernet cipher using machine-specific key.

        Returns:
            Fernet cipher instance
        """
        # Derive key from machine identifier
        machine_id = self._get_machine_id()
        salt = b'openbench_wizard_salt'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        return Fernet(key)

    def _get_machine_id(self) -> str:
        """Get machine identifier for key derivation.

        Returns:
            Machine identifier string
        """
        import uuid
        # Use MAC address + username as identifier
        mac = uuid.getnode()
        user = getpass.getuser()
        return f"{mac}:{user}"

    def _load_credentials(self) -> Dict[str, Any]:
        """Load credentials from file.

        Returns:
            Credentials dictionary
        """
        if not os.path.exists(self._credentials_path):
            return {"servers": {}}

        try:
            with open(self._credentials_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {"servers": {}}

    def _save_credentials(self, data: Dict[str, Any]) -> None:
        """Save credentials to file.

        Args:
            data: Credentials dictionary
        """
        os.makedirs(self._config_dir, exist_ok=True)
        with open(self._credentials_path, 'w') as f:
            json.dump(data, f, indent=2)
        # Set file permissions to 600 (user only)
        os.chmod(self._credentials_path, 0o600)

    def save_credential(
        self,
        host: str,
        auth_type: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        jump_node: Optional[str] = None,
        jump_auth: str = "none"
    ) -> None:
        """Save credential for a host.

        Args:
            host: Host string (user@host)
            auth_type: Authentication type (password/key)
            password: Password (will be encrypted)
            key_file: SSH key file path
            jump_node: Jump/compute node name
            jump_auth: Jump authentication type
        """
        data = self._load_credentials()

        encrypted_password = None
        if password:
            encrypted_password = self._fernet.encrypt(password.encode()).decode()

        data["servers"][host] = {
            "auth_type": auth_type,
            "password": encrypted_password,
            "key_file": key_file,
            "jump_node": jump_node,
            "jump_auth": jump_auth
        }

        self._save_credentials(data)

    def get_credential(self, host: str) -> Optional[Dict[str, Any]]:
        """Get credential for a host.

        Args:
            host: Host string

        Returns:
            Credential dictionary or None
        """
        data = self._load_credentials()
        cred = data.get("servers", {}).get(host)

        if cred and cred.get("password"):
            try:
                decrypted = self._fernet.decrypt(cred["password"].encode()).decode()
                cred = cred.copy()
                cred["password"] = decrypted
            except Exception:
                cred["password"] = None

        return cred

    def delete_credential(self, host: str) -> None:
        """Delete credential for a host.

        Args:
            host: Host string
        """
        data = self._load_credentials()
        if host in data.get("servers", {}):
            del data["servers"][host]
            self._save_credentials(data)

    def clear_all(self) -> None:
        """Clear all saved credentials."""
        self._save_credentials({"servers": {}})

    def list_hosts(self) -> list:
        """List all saved hosts.

        Returns:
            List of host strings
        """
        data = self._load_credentials()
        return list(data.get("servers", {}).keys())
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_credential_manager.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/credential_manager.py tests/test_credential_manager.py
git commit -m "feat: add Credential Manager with encrypted storage"
```

---

## Task 8: Remote Config Widget

**Files:**
- Create: `ui/widgets/remote_config.py`

**Step 1: Create Remote Config UI widget**

Create `ui/widgets/remote_config.py`:
```python
# -*- coding: utf-8 -*-
"""
Remote server configuration widget.
"""

from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QRadioButton,
    QButtonGroup, QCheckBox, QComboBox, QLabel,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Signal, Qt

from core.ssh_manager import SSHManager, SSHConnectionError
from core.credential_manager import CredentialManager
from ui.widgets.path_selector import PathSelector


class RemoteConfigWidget(QWidget):
    """Widget for configuring remote server connection."""

    connection_changed = Signal(bool)  # Connected state changed
    config_changed = Signal()  # Configuration changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ssh_manager: Optional[SSHManager] = None
        self._credential_manager = CredentialManager()
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # === Remote Server Group ===
        server_group = QGroupBox("Remote Server")
        server_layout = QFormLayout(server_group)

        # Host input
        host_layout = QHBoxLayout()
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("user@192.168.1.100")
        self.host_input.textChanged.connect(self._on_config_changed)
        host_layout.addWidget(self.host_input)

        self.btn_test = QPushButton("Test")
        self.btn_test.setFixedWidth(60)
        self.btn_test.clicked.connect(self._test_connection)
        host_layout.addWidget(self.btn_test)

        server_layout.addRow("Host:", host_layout)

        # Authentication
        auth_layout = QHBoxLayout()
        self.auth_group = QButtonGroup(self)
        self.radio_password = QRadioButton("Password")
        self.radio_password.setChecked(True)
        self.radio_key = QRadioButton("SSH Key")
        self.auth_group.addButton(self.radio_password)
        self.auth_group.addButton(self.radio_key)
        self.radio_password.toggled.connect(self._on_auth_changed)
        auth_layout.addWidget(self.radio_password)
        auth_layout.addWidget(self.radio_key)
        auth_layout.addStretch()
        server_layout.addRow("Auth:", auth_layout)

        # Password input
        pwd_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Password")
        pwd_layout.addWidget(self.password_input)

        self.cb_save_password = QCheckBox("Save")
        self.cb_save_password.setToolTip("Save password (encrypted)")
        pwd_layout.addWidget(self.cb_save_password)

        self.password_row_widget = QWidget()
        self.password_row_widget.setLayout(pwd_layout)
        server_layout.addRow("", self.password_row_widget)

        # SSH Key input
        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("~/.ssh/id_rsa")
        key_layout.addWidget(self.key_input)

        self.btn_browse_key = QPushButton("Browse")
        self.btn_browse_key.setFixedWidth(60)
        self.btn_browse_key.clicked.connect(self._browse_key)
        key_layout.addWidget(self.btn_browse_key)

        self.key_row_widget = QWidget()
        self.key_row_widget.setLayout(key_layout)
        self.key_row_widget.hide()
        server_layout.addRow("", self.key_row_widget)

        # Connection status
        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("color: #999;")
        server_layout.addRow("Status:", self.status_label)

        layout.addWidget(server_group)

        # === Compute Node Group ===
        node_group = QGroupBox("Compute Node (Optional)")
        node_group.setCheckable(True)
        node_group.setChecked(False)
        node_group.toggled.connect(self._on_config_changed)
        self.node_group = node_group
        node_layout = QFormLayout(node_group)

        self.node_input = QLineEdit()
        self.node_input.setPlaceholderText("node110")
        self.node_input.textChanged.connect(self._on_config_changed)
        node_layout.addRow("Node:", self.node_input)

        # Node auth
        node_auth_layout = QHBoxLayout()
        self.node_auth_group = QButtonGroup(self)
        self.radio_node_none = QRadioButton("None (internal trust)")
        self.radio_node_none.setChecked(True)
        self.radio_node_password = QRadioButton("Password")
        self.node_auth_group.addButton(self.radio_node_none)
        self.node_auth_group.addButton(self.radio_node_password)
        node_auth_layout.addWidget(self.radio_node_none)
        node_auth_layout.addWidget(self.radio_node_password)
        node_auth_layout.addStretch()
        node_layout.addRow("Auth:", node_auth_layout)

        self.node_password_input = QLineEdit()
        self.node_password_input.setEchoMode(QLineEdit.Password)
        self.node_password_input.setPlaceholderText("Node password")
        self.node_password_input.hide()
        self.radio_node_password.toggled.connect(
            lambda checked: self.node_password_input.setVisible(checked)
        )
        node_layout.addRow("", self.node_password_input)

        layout.addWidget(node_group)

        # === Remote Python Environment ===
        env_group = QGroupBox("Remote Python Environment")
        env_layout = QFormLayout(env_group)

        # Python path
        python_layout = QHBoxLayout()
        self.python_combo = QComboBox()
        self.python_combo.setEditable(True)
        self.python_combo.setMinimumWidth(250)
        self.python_combo.currentTextChanged.connect(self._on_config_changed)
        python_layout.addWidget(self.python_combo)

        self.btn_detect_python = QPushButton("Detect")
        self.btn_detect_python.setFixedWidth(60)
        self.btn_detect_python.clicked.connect(self._detect_python)
        python_layout.addWidget(self.btn_detect_python)

        env_layout.addRow("Python:", python_layout)

        # Conda env
        conda_layout = QHBoxLayout()
        self.conda_combo = QComboBox()
        self.conda_combo.addItem("(Not using conda environment)")
        self.conda_combo.currentTextChanged.connect(self._on_config_changed)
        conda_layout.addWidget(self.conda_combo)

        self.btn_refresh_conda = QPushButton("Refresh")
        self.btn_refresh_conda.setFixedWidth(60)
        self.btn_refresh_conda.clicked.connect(self._refresh_conda)
        conda_layout.addWidget(self.btn_refresh_conda)

        env_layout.addRow("Conda:", conda_layout)

        # OpenBench path
        ob_layout = QHBoxLayout()
        self.openbench_input = QLineEdit()
        self.openbench_input.setPlaceholderText("/home/user/OpenBench")
        self.openbench_input.textChanged.connect(self._on_config_changed)
        ob_layout.addWidget(self.openbench_input)

        self.btn_install_ob = QPushButton("Install...")
        self.btn_install_ob.setFixedWidth(70)
        self.btn_install_ob.clicked.connect(self._install_openbench)
        ob_layout.addWidget(self.btn_install_ob)

        env_layout.addRow("OpenBench:", ob_layout)

        layout.addWidget(env_group)
        layout.addStretch()

    def _on_auth_changed(self, checked: bool):
        """Handle auth type change."""
        if self.radio_password.isChecked():
            self.password_row_widget.show()
            self.key_row_widget.hide()
        else:
            self.password_row_widget.hide()
            self.key_row_widget.show()
        self._on_config_changed()

    def _on_config_changed(self):
        """Handle configuration change."""
        self.config_changed.emit()

    def _browse_key(self):
        """Browse for SSH key file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select SSH Key",
            os.path.expanduser("~/.ssh"),
            "All Files (*)"
        )
        if path:
            self.key_input.setText(path)

    def _test_connection(self):
        """Test SSH connection."""
        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "Error", "Please enter host address")
            return

        try:
            self._ssh_manager = SSHManager()

            if self.radio_password.isChecked():
                password = self.password_input.text()
                self._ssh_manager.connect(host, password=password)
            else:
                key_file = self.key_input.text().strip()
                self._ssh_manager.connect(host, key_file=key_file)

            # Test jump connection if enabled
            if self.node_group.isChecked():
                node = self.node_input.text().strip()
                if node:
                    node_password = None
                    if self.radio_node_password.isChecked():
                        node_password = self.node_password_input.text()
                    self._ssh_manager.connect_jump(node, password=node_password)

            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: green;")
            self.connection_changed.emit(True)

            # Save credentials if requested
            if self.cb_save_password.isChecked():
                self._credential_manager.save_credential(
                    host=host,
                    auth_type="password" if self.radio_password.isChecked() else "key",
                    password=self.password_input.text() if self.radio_password.isChecked() else None,
                    key_file=self.key_input.text() if self.radio_key.isChecked() else None,
                    jump_node=self.node_input.text() if self.node_group.isChecked() else None,
                    jump_auth="password" if self.radio_node_password.isChecked() else "none"
                )

            QMessageBox.information(self, "Success", "Connection successful!")

        except SSHConnectionError as e:
            self.status_label.setText("Connection failed")
            self.status_label.setStyleSheet("color: red;")
            self.connection_changed.emit(False)
            QMessageBox.critical(self, "Connection Failed", str(e))

    def _detect_python(self):
        """Detect Python interpreters on remote server."""
        if not self._ssh_manager or not self._ssh_manager.is_connected:
            QMessageBox.warning(self, "Error", "Please connect to server first")
            return

        try:
            pythons = self._ssh_manager.detect_python_interpreters()
            self.python_combo.clear()
            for p in pythons:
                self.python_combo.addItem(p)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to detect Python: {e}")

    def _refresh_conda(self):
        """Refresh conda environments."""
        if not self._ssh_manager or not self._ssh_manager.is_connected:
            QMessageBox.warning(self, "Error", "Please connect to server first")
            return

        try:
            envs = self._ssh_manager.detect_conda_envs()
            self.conda_combo.clear()
            self.conda_combo.addItem("(Not using conda environment)")
            for name, path in envs:
                self.conda_combo.addItem(name, path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to refresh: {e}")

    def _install_openbench(self):
        """Open OpenBench installation dialog."""
        # TODO: Implement installation dialog
        QMessageBox.information(
            self, "Coming Soon",
            "OpenBench installation wizard will be implemented."
        )

    def get_ssh_manager(self) -> Optional[SSHManager]:
        """Get SSH manager instance."""
        return self._ssh_manager

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "host": self.host_input.text().strip(),
            "auth_type": "password" if self.radio_password.isChecked() else "key",
            "use_jump": self.node_group.isChecked(),
            "jump_node": self.node_input.text().strip(),
            "jump_auth": "password" if self.radio_node_password.isChecked() else "none",
            "python_path": self.python_combo.currentText(),
            "conda_env": self.conda_combo.currentText() if self.conda_combo.currentIndex() > 0 else "",
            "openbench_path": self.openbench_input.text().strip(),
        }

    def set_config(self, config: Dict[str, Any]):
        """Set configuration."""
        self.host_input.setText(config.get("host", ""))

        if config.get("auth_type") == "key":
            self.radio_key.setChecked(True)
        else:
            self.radio_password.setChecked(True)

        self.node_group.setChecked(config.get("use_jump", False))
        self.node_input.setText(config.get("jump_node", ""))

        if config.get("jump_auth") == "password":
            self.radio_node_password.setChecked(True)
        else:
            self.radio_node_none.setChecked(True)

        if config.get("python_path"):
            self.python_combo.setCurrentText(config["python_path"])
        if config.get("conda_env"):
            idx = self.conda_combo.findText(config["conda_env"])
            if idx >= 0:
                self.conda_combo.setCurrentIndex(idx)
        self.openbench_input.setText(config.get("openbench_path", ""))

        # Try to load saved credentials
        host = config.get("host", "")
        if host:
            cred = self._credential_manager.get_credential(host)
            if cred:
                if cred.get("password"):
                    self.password_input.setText(cred["password"])
                    self.cb_save_password.setChecked(True)
                if cred.get("key_file"):
                    self.key_input.setText(cred["key_file"])
```

**Step 2: Commit**

```bash
git add ui/widgets/remote_config.py
git commit -m "feat: add Remote Config UI widget"
```

---

## Task 9: Update page_general.py for Remote Mode

**Files:**
- Modify: `ui/pages/page_general.py`

**Step 1: Add execution mode toggle and remote config widget**

This task integrates the RemoteConfigWidget into the General Settings page. Add execution mode radio buttons and show/hide the remote config based on selection.

(Implementation details follow the design document UI section)

**Step 2: Commit**

```bash
git add ui/pages/page_general.py
git commit -m "feat: integrate remote execution UI into General Settings"
```

---

## Task 10: Create Remote Runner

**Files:**
- Create: `core/remote_runner.py`

**Step 1: Create Remote Runner that mirrors EvaluationRunner interface**

The RemoteRunner should:
- Upload config files to remote server
- Execute OpenBench via SSH
- Stream logs back in real-time
- Handle errors and cleanup

(Implementation follows the execution flow in design document)

**Step 2: Commit**

```bash
git add core/remote_runner.py
git commit -m "feat: add Remote Runner for SSH-based execution"
```

---

## Task 11: Update Run Monitor for Remote Execution

**Files:**
- Modify: `ui/pages/page_run_monitor.py`

**Step 1: Update to support both local and remote runners**

Check execution mode from config and use appropriate runner.

**Step 2: Commit**

```bash
git add ui/pages/page_run_monitor.py
git commit -m "feat: support remote execution in Run Monitor"
```

---

## Task 12: Wizard Config Manager

**Files:**
- Modify: `core/config_manager.py`

**Step 1: Add .wizard.yaml read/write support**

Add methods to read and write `.wizard.yaml` separately from main config.

**Step 2: Commit**

```bash
git add core/config_manager.py
git commit -m "feat: add .wizard.yaml support in Config Manager"
```

---

## Task 13: Integration Testing

**Files:**
- Create: `tests/test_remote_integration.py`

**Step 1: Create integration tests**

Test the full flow with mocked SSH connections.

**Step 2: Commit**

```bash
git add tests/test_remote_integration.py
git commit -m "test: add remote execution integration tests"
```

---

## Summary

**Total Tasks:** 13
**New Files:** 7
**Modified Files:** 5

**Implementation Order:**
1. Dependencies
2. SSH Manager (Tasks 2-6)
3. Credential Manager (Task 7)
4. UI Components (Tasks 8-9)
5. Remote Runner (Task 10)
6. Integration (Tasks 11-13)
