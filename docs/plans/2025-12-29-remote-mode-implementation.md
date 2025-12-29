# Remote Mode Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor remote mode so the server is the source of truth, with GUI as a remote editor that caches locally and syncs asynchronously.

**Architecture:** Unified `ProjectStorage` interface abstracts local/remote differences. `RemoteStorage` uses `SyncEngine` for local caching and background sync. UI layer remains unchanged.

**Tech Stack:** PySide6, paramiko (SSH), PyYAML, threading (background sync)

---

## Task 1: Create ProjectStorage Abstract Interface

**Files:**
- Create: `core/storage.py`
- Test: `tests/test_storage.py`

**Step 1: Write the failing test**

```python
# tests/test_storage.py
import pytest
from core.storage import ProjectStorage, LocalStorage

def test_local_storage_read_file(tmp_path):
    """Test LocalStorage can read a file."""
    test_file = tmp_path / "test.yaml"
    test_file.write_text("key: value")

    storage = LocalStorage(str(tmp_path))
    content = storage.read_file("test.yaml")

    assert content == "key: value"

def test_local_storage_write_file(tmp_path):
    """Test LocalStorage can write a file."""
    storage = LocalStorage(str(tmp_path))
    storage.write_file("output.yaml", "new: content")

    result = (tmp_path / "output.yaml").read_text()
    assert result == "new: content"

def test_local_storage_list_dir(tmp_path):
    """Test LocalStorage can list directory contents."""
    (tmp_path / "file1.yaml").touch()
    (tmp_path / "file2.yaml").touch()
    (tmp_path / "subdir").mkdir()

    storage = LocalStorage(str(tmp_path))
    items = storage.list_dir("")

    assert "file1.yaml" in items
    assert "file2.yaml" in items
    assert "subdir" in items

def test_local_storage_exists(tmp_path):
    """Test LocalStorage can check if path exists."""
    (tmp_path / "exists.yaml").touch()

    storage = LocalStorage(str(tmp_path))

    assert storage.exists("exists.yaml") is True
    assert storage.exists("missing.yaml") is False

def test_local_storage_glob(tmp_path):
    """Test LocalStorage can glob files."""
    (tmp_path / "nml").mkdir()
    (tmp_path / "nml" / "main.yaml").touch()
    (tmp_path / "nml" / "ref.yaml").touch()
    (tmp_path / "nml" / "other.txt").touch()

    storage = LocalStorage(str(tmp_path))
    matches = storage.glob("nml/*.yaml")

    assert len(matches) == 2
    assert any("main.yaml" in m for m in matches)
    assert any("ref.yaml" in m for m in matches)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_storage.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core.storage'"

**Step 3: Write minimal implementation**

```python
# core/storage.py
# -*- coding: utf-8 -*-
"""
Unified storage interface for local and remote file operations.
"""

import os
import glob as glob_module
from abc import ABC, abstractmethod
from typing import List, Optional


class ProjectStorage(ABC):
    """Abstract interface for project file storage operations."""

    def __init__(self, project_dir: str):
        """
        Initialize storage with project directory.

        Args:
            project_dir: Base directory for all operations
        """
        self._project_dir = project_dir

    @property
    def project_dir(self) -> str:
        """Get the project directory."""
        return self._project_dir

    @abstractmethod
    def read_file(self, path: str) -> str:
        """
        Read file contents.

        Args:
            path: Relative path from project directory

        Returns:
            File contents as string
        """
        pass

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """
        Write content to file.

        Args:
            path: Relative path from project directory
            content: Content to write
        """
        pass

    @abstractmethod
    def list_dir(self, path: str) -> List[str]:
        """
        List directory contents.

        Args:
            path: Relative path from project directory

        Returns:
            List of file/directory names
        """
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Check if path exists.

        Args:
            path: Relative path from project directory

        Returns:
            True if path exists
        """
        pass

    @abstractmethod
    def glob(self, pattern: str) -> List[str]:
        """
        Find files matching pattern.

        Args:
            pattern: Glob pattern (e.g., "nml/*.yaml")

        Returns:
            List of matching paths relative to project directory
        """
        pass

    @abstractmethod
    def mkdir(self, path: str) -> None:
        """
        Create directory (including parents).

        Args:
            path: Relative path from project directory
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """
        Delete file or empty directory.

        Args:
            path: Relative path from project directory
        """
        pass


class LocalStorage(ProjectStorage):
    """Storage implementation for local filesystem."""

    def _full_path(self, path: str) -> str:
        """Get full path from relative path."""
        if not path:
            return self._project_dir
        return os.path.join(self._project_dir, path)

    def read_file(self, path: str) -> str:
        full_path = self._full_path(path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_file(self, path: str, content: str) -> None:
        full_path = self._full_path(path)
        # Ensure directory exists
        dir_path = os.path.dirname(full_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def list_dir(self, path: str) -> List[str]:
        full_path = self._full_path(path)
        if not os.path.isdir(full_path):
            return []
        return os.listdir(full_path)

    def exists(self, path: str) -> bool:
        return os.path.exists(self._full_path(path))

    def glob(self, pattern: str) -> List[str]:
        full_pattern = self._full_path(pattern)
        matches = glob_module.glob(full_pattern)
        # Return paths relative to project directory
        return [os.path.relpath(m, self._project_dir) for m in matches]

    def mkdir(self, path: str) -> None:
        os.makedirs(self._full_path(path), exist_ok=True)

    def delete(self, path: str) -> None:
        full_path = self._full_path(path)
        if os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path):
            os.rmdir(full_path)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_storage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/storage.py tests/test_storage.py
git commit -m "$(cat <<'EOF'
feat: add ProjectStorage interface and LocalStorage implementation

Unified storage abstraction for local/remote file operations.
LocalStorage wraps standard filesystem operations.
EOF
)"
```

---

## Task 2: Create SyncEngine for Remote Caching

**Files:**
- Create: `core/sync_engine.py`
- Test: `tests/test_sync_engine.py`

**Step 1: Write the failing test**

```python
# tests/test_sync_engine.py
import pytest
import time
from unittest.mock import Mock, MagicMock
from core.sync_engine import SyncEngine, SyncStatus

def test_sync_engine_cache_write():
    """Test SyncEngine caches writes locally."""
    ssh_mock = Mock()
    engine = SyncEngine(ssh_mock, "/remote/project")

    engine.write("test.yaml", "content: value")

    # Should be cached locally
    assert engine.read("test.yaml") == "content: value"
    # Should be marked dirty
    assert engine.get_sync_status("test.yaml") == SyncStatus.PENDING

def test_sync_engine_cache_read():
    """Test SyncEngine reads from cache first."""
    ssh_mock = Mock()
    engine = SyncEngine(ssh_mock, "/remote/project")

    # Pre-populate cache
    engine._cache["test.yaml"] = "cached content"
    engine._sync_status["test.yaml"] = SyncStatus.SYNCED

    # Should not call SSH
    content = engine.read("test.yaml")

    assert content == "cached content"
    ssh_mock.execute.assert_not_called()

def test_sync_engine_fetch_on_miss():
    """Test SyncEngine fetches from remote on cache miss."""
    ssh_mock = Mock()
    ssh_mock.execute.return_value = ("remote content", "", 0)

    engine = SyncEngine(ssh_mock, "/remote/project")
    content = engine.read("missing.yaml")

    assert content == "remote content"
    ssh_mock.execute.assert_called_once()

def test_sync_engine_sync_pending():
    """Test SyncEngine syncs pending changes."""
    ssh_mock = Mock()
    ssh_mock.execute.return_value = ("", "", 0)

    engine = SyncEngine(ssh_mock, "/remote/project")
    engine.write("file1.yaml", "content1")
    engine.write("file2.yaml", "content2")

    # Sync all pending
    engine.sync_all()

    # Should have called execute for directory creation and file writes
    assert ssh_mock.execute.call_count >= 2
    # Status should be synced
    assert engine.get_sync_status("file1.yaml") == SyncStatus.SYNCED
    assert engine.get_sync_status("file2.yaml") == SyncStatus.SYNCED
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_sync_engine.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core.sync_engine'"

**Step 3: Write minimal implementation**

```python
# core/sync_engine.py
# -*- coding: utf-8 -*-
"""
Sync engine for remote storage with local caching.
"""

import os
import threading
import logging
from enum import Enum
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """Sync status for a file."""
    SYNCED = "synced"      # File is synced with remote
    PENDING = "pending"    # Local changes not yet synced
    SYNCING = "syncing"    # Currently syncing
    ERROR = "error"        # Sync failed


@dataclass
class SyncState:
    """State of a file in the sync engine."""
    status: SyncStatus
    error_message: Optional[str] = None
    retry_count: int = 0


class SyncEngine:
    """
    Manages local cache and background sync with remote server.

    Provides immediate local reads/writes with async sync to remote.
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        ssh_manager,
        remote_project_dir: str,
        on_status_changed: Optional[Callable[[str, SyncStatus], None]] = None
    ):
        """
        Initialize sync engine.

        Args:
            ssh_manager: SSH manager for remote operations
            remote_project_dir: Remote project directory path
            on_status_changed: Callback when file sync status changes
        """
        self._ssh = ssh_manager
        self._remote_dir = remote_project_dir.rstrip('/')
        self._on_status_changed = on_status_changed

        # Cache storage
        self._cache: Dict[str, str] = {}
        self._sync_status: Dict[str, SyncStatus] = {}
        self._sync_errors: Dict[str, str] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Background sync
        self._pending_sync: Set[str] = set()
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_sync = threading.Event()

    def _remote_path(self, path: str) -> str:
        """Get full remote path."""
        if not path:
            return self._remote_dir
        return f"{self._remote_dir}/{path}"

    def read(self, path: str) -> str:
        """
        Read file, from cache if available, otherwise from remote.

        Args:
            path: Relative path from project directory

        Returns:
            File contents
        """
        with self._lock:
            # Check cache first
            if path in self._cache:
                return self._cache[path]

        # Fetch from remote
        remote_path = self._remote_path(path)
        stdout, stderr, exit_code = self._ssh.execute(
            f"cat '{remote_path}'", timeout=30
        )

        if exit_code != 0:
            raise FileNotFoundError(f"Remote file not found: {remote_path}")

        content = stdout

        with self._lock:
            self._cache[path] = content
            self._sync_status[path] = SyncStatus.SYNCED

        return content

    def write(self, path: str, content: str) -> None:
        """
        Write to local cache and queue for sync.

        Args:
            path: Relative path from project directory
            content: Content to write
        """
        with self._lock:
            self._cache[path] = content
            self._sync_status[path] = SyncStatus.PENDING
            self._pending_sync.add(path)

        self._notify_status_changed(path, SyncStatus.PENDING)

    def get_sync_status(self, path: str) -> SyncStatus:
        """Get sync status for a file."""
        with self._lock:
            return self._sync_status.get(path, SyncStatus.SYNCED)

    def get_overall_status(self) -> SyncStatus:
        """Get overall sync status."""
        with self._lock:
            statuses = set(self._sync_status.values())
            if SyncStatus.ERROR in statuses:
                return SyncStatus.ERROR
            if SyncStatus.SYNCING in statuses:
                return SyncStatus.SYNCING
            if SyncStatus.PENDING in statuses:
                return SyncStatus.PENDING
            return SyncStatus.SYNCED

    def sync_all(self) -> bool:
        """
        Sync all pending changes to remote.

        Returns:
            True if all syncs succeeded
        """
        with self._lock:
            pending = list(self._pending_sync)

        success = True
        for path in pending:
            if not self._sync_file(path):
                success = False

        return success

    def _sync_file(self, path: str) -> bool:
        """
        Sync a single file to remote.

        Returns:
            True if sync succeeded
        """
        with self._lock:
            if path not in self._cache:
                return True
            content = self._cache[path]
            self._sync_status[path] = SyncStatus.SYNCING

        self._notify_status_changed(path, SyncStatus.SYNCING)

        try:
            remote_path = self._remote_path(path)

            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self._ssh.execute(f"mkdir -p '{remote_dir}'", timeout=10)

            # Write content using heredoc
            # Escape single quotes in content
            escaped = content.replace("'", "'\"'\"'")
            cmd = f"cat > '{remote_path}' << 'EOFCONTENT'\n{content}\nEOFCONTENT"
            stdout, stderr, exit_code = self._ssh.execute(cmd, timeout=30)

            if exit_code != 0:
                raise Exception(f"Write failed: {stderr}")

            with self._lock:
                self._sync_status[path] = SyncStatus.SYNCED
                self._pending_sync.discard(path)
                self._sync_errors.pop(path, None)

            self._notify_status_changed(path, SyncStatus.SYNCED)
            return True

        except Exception as e:
            logger.error(f"Sync failed for {path}: {e}")
            with self._lock:
                self._sync_status[path] = SyncStatus.ERROR
                self._sync_errors[path] = str(e)
            self._notify_status_changed(path, SyncStatus.ERROR)
            return False

    def _notify_status_changed(self, path: str, status: SyncStatus):
        """Notify callback of status change."""
        if self._on_status_changed:
            try:
                self._on_status_changed(path, status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def list_dir(self, path: str) -> List[str]:
        """List remote directory contents."""
        remote_path = self._remote_path(path)
        stdout, stderr, exit_code = self._ssh.execute(
            f"ls -1 '{remote_path}' 2>/dev/null", timeout=30
        )
        if exit_code != 0:
            return []
        return [line.strip() for line in stdout.strip().split('\n') if line.strip()]

    def exists(self, path: str) -> bool:
        """Check if remote path exists."""
        # Check cache first
        with self._lock:
            if path in self._cache:
                return True

        remote_path = self._remote_path(path)
        stdout, stderr, exit_code = self._ssh.execute(
            f"test -e '{remote_path}' && echo 'exists'", timeout=10
        )
        return exit_code == 0 and 'exists' in stdout

    def glob(self, pattern: str) -> List[str]:
        """Find files matching pattern on remote."""
        remote_pattern = self._remote_path(pattern)
        # Use find with -path for glob-like matching
        base_dir = self._remote_dir
        stdout, stderr, exit_code = self._ssh.execute(
            f"cd '{base_dir}' && find . -path './{pattern}' -type f 2>/dev/null | sed 's|^\\./||'",
            timeout=30
        )
        if exit_code != 0:
            return []
        return [line.strip() for line in stdout.strip().split('\n') if line.strip()]

    def mkdir(self, path: str) -> None:
        """Create remote directory."""
        remote_path = self._remote_path(path)
        self._ssh.execute(f"mkdir -p '{remote_path}'", timeout=10)

    def delete(self, path: str) -> None:
        """Delete remote file or directory."""
        remote_path = self._remote_path(path)
        self._ssh.execute(f"rm -f '{remote_path}'", timeout=10)

        with self._lock:
            self._cache.pop(path, None)
            self._sync_status.pop(path, None)
            self._pending_sync.discard(path)

    def start_background_sync(self, interval: float = 2.0):
        """Start background sync thread."""
        if self._sync_thread and self._sync_thread.is_alive():
            return

        self._stop_sync.clear()
        self._sync_thread = threading.Thread(
            target=self._background_sync_loop,
            args=(interval,),
            daemon=True
        )
        self._sync_thread.start()

    def stop_background_sync(self):
        """Stop background sync thread."""
        self._stop_sync.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)

    def _background_sync_loop(self, interval: float):
        """Background sync loop."""
        while not self._stop_sync.wait(interval):
            with self._lock:
                pending = list(self._pending_sync)

            for path in pending:
                if self._stop_sync.is_set():
                    break
                self._sync_file(path)

    def load_project(self) -> None:
        """
        Load all project files into cache.

        Call this when opening a remote project.
        """
        # Load nml directory structure
        nml_files = self.glob("nml/**/*.yaml")
        for path in nml_files:
            try:
                self.read(path)
            except Exception as e:
                logger.warning(f"Failed to load {path}: {e}")

    def get_pending_count(self) -> int:
        """Get number of files pending sync."""
        with self._lock:
            return len(self._pending_sync)

    def get_error_files(self) -> Dict[str, str]:
        """Get files with sync errors and their error messages."""
        with self._lock:
            return dict(self._sync_errors)

    def retry_errors(self) -> bool:
        """Retry syncing files that had errors."""
        with self._lock:
            error_files = [
                path for path, status in self._sync_status.items()
                if status == SyncStatus.ERROR
            ]

        success = True
        for path in error_files:
            if not self._sync_file(path):
                success = False

        return success
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_sync_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/sync_engine.py tests/test_sync_engine.py
git commit -m "$(cat <<'EOF'
feat: add SyncEngine for remote caching and background sync

Provides local cache with async sync to remote server.
Supports background sync thread and retry on error.
EOF
)"
```

---

## Task 3: Create RemoteStorage Implementation

**Files:**
- Modify: `core/storage.py`
- Test: `tests/test_storage.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_storage.py
from unittest.mock import Mock, MagicMock
from core.storage import RemoteStorage

def test_remote_storage_read_file():
    """Test RemoteStorage can read a file via SyncEngine."""
    sync_engine = Mock()
    sync_engine.read.return_value = "remote content"

    storage = RemoteStorage("/remote/project", sync_engine)
    content = storage.read_file("test.yaml")

    assert content == "remote content"
    sync_engine.read.assert_called_once_with("test.yaml")

def test_remote_storage_write_file():
    """Test RemoteStorage can write a file via SyncEngine."""
    sync_engine = Mock()

    storage = RemoteStorage("/remote/project", sync_engine)
    storage.write_file("output.yaml", "new content")

    sync_engine.write.assert_called_once_with("output.yaml", "new content")

def test_remote_storage_list_dir():
    """Test RemoteStorage can list directory via SyncEngine."""
    sync_engine = Mock()
    sync_engine.list_dir.return_value = ["file1.yaml", "file2.yaml"]

    storage = RemoteStorage("/remote/project", sync_engine)
    items = storage.list_dir("nml")

    assert items == ["file1.yaml", "file2.yaml"]
    sync_engine.list_dir.assert_called_once_with("nml")
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_storage.py::test_remote_storage_read_file -v`
Expected: FAIL with "cannot import name 'RemoteStorage'"

**Step 3: Write minimal implementation**

Add to `core/storage.py`:

```python
# Add import at top
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.sync_engine import SyncEngine

# Add RemoteStorage class at end of file
class RemoteStorage(ProjectStorage):
    """Storage implementation for remote server via SyncEngine."""

    def __init__(self, project_dir: str, sync_engine: 'SyncEngine'):
        """
        Initialize remote storage.

        Args:
            project_dir: Remote project directory path
            sync_engine: SyncEngine instance for caching and sync
        """
        super().__init__(project_dir)
        self._sync = sync_engine

    @property
    def sync_engine(self) -> 'SyncEngine':
        """Get the sync engine."""
        return self._sync

    def read_file(self, path: str) -> str:
        return self._sync.read(path)

    def write_file(self, path: str, content: str) -> None:
        self._sync.write(path, content)

    def list_dir(self, path: str) -> List[str]:
        return self._sync.list_dir(path)

    def exists(self, path: str) -> bool:
        return self._sync.exists(path)

    def glob(self, pattern: str) -> List[str]:
        return self._sync.glob(pattern)

    def mkdir(self, path: str) -> None:
        self._sync.mkdir(path)

    def delete(self, path: str) -> None:
        self._sync.delete(path)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_storage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/storage.py tests/test_storage.py
git commit -m "$(cat <<'EOF'
feat: add RemoteStorage implementation using SyncEngine

RemoteStorage wraps SyncEngine for unified storage interface.
EOF
)"
```

---

## Task 4: Create Sync Status Widget

**Files:**
- Create: `ui/widgets/sync_status.py`

**Step 1: Write the implementation**

```python
# ui/widgets/sync_status.py
# -*- coding: utf-8 -*-
"""
Sync status indicator widget for remote mode.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QColor

from core.sync_engine import SyncStatus


class SyncStatusWidget(QWidget):
    """Widget showing sync status with retry button."""

    retry_clicked = Signal()

    STATUS_COLORS = {
        SyncStatus.SYNCED: "#27ae60",   # Green
        SyncStatus.PENDING: "#f39c12",  # Yellow/Orange
        SyncStatus.SYNCING: "#3498db",  # Blue
        SyncStatus.ERROR: "#e74c3c",    # Red
    }

    STATUS_TEXT = {
        SyncStatus.SYNCED: "Synced",
        SyncStatus.PENDING: "Pending...",
        SyncStatus.SYNCING: "Syncing...",
        SyncStatus.ERROR: "Sync Error",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = SyncStatus.SYNCED
        self._pending_count = 0
        self._setup_ui()

        # Animation timer for syncing state
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_frame = 0

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Status indicator (colored dot)
        self._dot = QLabel()
        self._dot.setFixedSize(12, 12)
        self._dot.setStyleSheet(self._get_dot_style(SyncStatus.SYNCED))
        layout.addWidget(self._dot)

        # Status text
        self._text = QLabel("Synced")
        self._text.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(self._text)

        # Retry button (hidden by default)
        self._retry_btn = QPushButton("Retry")
        self._retry_btn.setFixedWidth(60)
        self._retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self._retry_btn.clicked.connect(self.retry_clicked.emit)
        self._retry_btn.setVisible(False)
        layout.addWidget(self._retry_btn)

        layout.addStretch()

    def _get_dot_style(self, status: SyncStatus) -> str:
        color = self.STATUS_COLORS.get(status, "#666666")
        return f"""
            background-color: {color};
            border-radius: 6px;
        """

    def set_status(self, status: SyncStatus, pending_count: int = 0):
        """Update the sync status display."""
        self._status = status
        self._pending_count = pending_count

        # Update dot color
        self._dot.setStyleSheet(self._get_dot_style(status))

        # Update text
        text = self.STATUS_TEXT.get(status, "Unknown")
        if status == SyncStatus.PENDING and pending_count > 0:
            text = f"Pending ({pending_count})"
        self._text.setText(text)

        # Show/hide retry button
        self._retry_btn.setVisible(status == SyncStatus.ERROR)

        # Start/stop animation
        if status == SyncStatus.SYNCING:
            self._animation_timer.start(200)
        else:
            self._animation_timer.stop()
            self._animation_frame = 0

    def _animate(self):
        """Animate the syncing indicator."""
        self._animation_frame = (self._animation_frame + 1) % 4
        dots = "." * (self._animation_frame + 1)
        self._text.setText(f"Syncing{dots}")

    def set_hidden_when_synced(self, hidden: bool):
        """Hide the widget when status is synced."""
        if hidden and self._status == SyncStatus.SYNCED:
            self.setVisible(False)
        else:
            self.setVisible(True)
```

**Step 2: Commit**

```bash
git add ui/widgets/sync_status.py
git commit -m "$(cat <<'EOF'
feat: add SyncStatusWidget for remote sync indication

Shows sync status with colored indicator, pending count,
and retry button for error states.
EOF
)"
```

---

## Task 5: Create Path Autocomplete Widget

**Files:**
- Create: `ui/widgets/path_completer.py`

**Step 1: Write the implementation**

```python
# ui/widgets/path_completer.py
# -*- coding: utf-8 -*-
"""
Path autocomplete for storage-backed path input.
"""

import os
from typing import Optional, List
from PySide6.QtWidgets import QCompleter
from PySide6.QtCore import Qt, QStringListModel, QTimer

from core.storage import ProjectStorage


class PathCompleterModel(QStringListModel):
    """Model that fetches path completions from storage."""

    def __init__(self, storage: Optional[ProjectStorage] = None, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._cache: dict = {}
        self._base_path = ""

    def set_storage(self, storage: Optional[ProjectStorage]):
        """Set the storage backend."""
        self._storage = storage
        self._cache.clear()

    def update_completions(self, text: str) -> List[str]:
        """
        Update completions for the given text.

        Args:
            text: Current input text

        Returns:
            List of completion suggestions
        """
        if not self._storage or not text:
            self.setStringList([])
            return []

        # Get directory part and prefix
        if '/' in text:
            dir_part = text.rsplit('/', 1)[0]
            prefix = text.rsplit('/', 1)[1] if '/' in text else text
        else:
            dir_part = ""
            prefix = text

        # Check cache
        cache_key = dir_part
        if cache_key not in self._cache:
            try:
                items = self._storage.list_dir(dir_part)
                self._cache[cache_key] = items
            except Exception:
                self._cache[cache_key] = []

        items = self._cache.get(cache_key, [])

        # Filter by prefix and build full paths
        completions = []
        for item in items:
            if item.lower().startswith(prefix.lower()):
                if dir_part:
                    full_path = f"{dir_part}/{item}"
                else:
                    full_path = item
                completions.append(full_path)

        # Sort: directories first, then files
        completions.sort(key=lambda x: (not x.endswith('/'), x.lower()))

        self.setStringList(completions)
        return completions


class PathCompleter(QCompleter):
    """
    Path completer with delayed fetching for storage backends.
    """

    DELAY_MS = 300  # Delay before fetching completions

    def __init__(self, storage: Optional[ProjectStorage] = None, parent=None):
        self._model = PathCompleterModel(storage, parent)
        super().__init__(self._model, parent)

        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.setFilterMode(Qt.MatchStartsWith)

        # Delay timer for remote fetching
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._fetch_completions)
        self._pending_text = ""

    def set_storage(self, storage: Optional[ProjectStorage]):
        """Set the storage backend."""
        self._model.set_storage(storage)

    def update_completions(self, text: str):
        """
        Request completion update for text.

        Uses delayed fetching to avoid excessive remote calls.
        """
        self._pending_text = text
        self._delay_timer.start(self.DELAY_MS)

    def _fetch_completions(self):
        """Fetch completions after delay."""
        self._model.update_completions(self._pending_text)

    def clear_cache(self):
        """Clear the completion cache."""
        self._model._cache.clear()
```

**Step 2: Commit**

```bash
git add ui/widgets/path_completer.py
git commit -m "$(cat <<'EOF'
feat: add PathCompleter for storage-backed autocomplete

Provides path autocomplete with delayed fetching for remote storage.
Caches directory listings to minimize remote calls.
EOF
)"
```

---

## Task 6: Create Project Selector Dialog

**Files:**
- Create: `ui/dialogs/project_selector.py`

**Step 1: Write the implementation**

```python
# ui/dialogs/project_selector.py
# -*- coding: utf-8 -*-
"""
Project selector dialog for startup.
"""

import os
import yaml
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget, QWidget,
    QLineEdit, QMessageBox, QFileDialog, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal

from core.storage import ProjectStorage, LocalStorage, RemoteStorage
from core.sync_engine import SyncEngine
from ui.widgets.remote_config import RemoteConfigWidget, RemoteFileBrowser


class ProjectSelectorDialog(QDialog):
    """Dialog for selecting or creating a project."""

    # Signal emitted when project is selected: (storage, project_name)
    project_selected = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenBench Wizard - Select Project")
        self.setMinimumSize(600, 500)
        self._storage: Optional[ProjectStorage] = None
        self._project_name = ""

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Select Project Type")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Mode selection buttons
        mode_layout = QHBoxLayout()

        self._btn_local = QPushButton("Local Project")
        self._btn_local.setMinimumHeight(60)
        self._btn_local.setCheckable(True)
        self._btn_local.setChecked(True)
        self._btn_local.setStyleSheet(self._get_mode_button_style())
        mode_layout.addWidget(self._btn_local)

        self._btn_remote = QPushButton("Remote Project")
        self._btn_remote.setMinimumHeight(60)
        self._btn_remote.setCheckable(True)
        self._btn_remote.setStyleSheet(self._get_mode_button_style())
        mode_layout.addWidget(self._btn_remote)

        layout.addLayout(mode_layout)

        # Stacked widget for mode-specific content
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # Local mode page
        self._local_page = self._create_local_page()
        self._stack.addWidget(self._local_page)

        # Remote mode page
        self._remote_page = self._create_remote_page()
        self._stack.addWidget(self._remote_page)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setMinimumWidth(100)
        btn_layout.addWidget(self._btn_cancel)

        self._btn_open = QPushButton("Open Project")
        self._btn_open.setMinimumWidth(120)
        self._btn_open.setDefault(True)
        btn_layout.addWidget(self._btn_open)

        layout.addLayout(btn_layout)

    def _get_mode_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #3498db;
                color: white;
                border-color: #2980b9;
            }
        """

    def _create_local_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Project directory selection
        dir_group = QGroupBox("Project Directory")
        dir_layout = QVBoxLayout(dir_group)

        path_layout = QHBoxLayout()
        self._local_path = QLineEdit()
        self._local_path.setPlaceholderText("Select project directory containing nml/ folder")
        path_layout.addWidget(self._local_path)

        self._btn_browse_local = QPushButton("Browse...")
        self._btn_browse_local.setFixedWidth(100)
        path_layout.addWidget(self._btn_browse_local)

        dir_layout.addLayout(path_layout)

        # New project option
        new_layout = QHBoxLayout()
        new_layout.addWidget(QLabel("Or create new project:"))
        self._btn_new_local = QPushButton("New Project...")
        new_layout.addWidget(self._btn_new_local)
        new_layout.addStretch()
        dir_layout.addLayout(new_layout)

        layout.addWidget(dir_group)
        layout.addStretch()

        return page

    def _create_remote_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # SSH Connection
        self._remote_config = RemoteConfigWidget()
        layout.addWidget(self._remote_config)

        # Remote project path
        path_group = QGroupBox("Remote Project Directory")
        path_layout = QVBoxLayout(path_group)

        remote_path_layout = QHBoxLayout()
        self._remote_path = QLineEdit()
        self._remote_path.setPlaceholderText("Select remote project directory")
        self._remote_path.setEnabled(False)
        remote_path_layout.addWidget(self._remote_path)

        self._btn_browse_remote = QPushButton("Browse...")
        self._btn_browse_remote.setFixedWidth(100)
        self._btn_browse_remote.setEnabled(False)
        remote_path_layout.addWidget(self._btn_browse_remote)

        path_layout.addLayout(remote_path_layout)

        # New project option
        new_layout = QHBoxLayout()
        new_layout.addWidget(QLabel("Or create new project:"))
        self._btn_new_remote = QPushButton("New Project...")
        self._btn_new_remote.setEnabled(False)
        new_layout.addWidget(self._btn_new_remote)
        new_layout.addStretch()
        path_layout.addLayout(new_layout)

        layout.addWidget(path_group)
        layout.addStretch()

        return page

    def _connect_signals(self):
        # Mode selection
        self._btn_local.clicked.connect(lambda: self._set_mode("local"))
        self._btn_remote.clicked.connect(lambda: self._set_mode("remote"))

        # Local mode
        self._btn_browse_local.clicked.connect(self._browse_local)
        self._btn_new_local.clicked.connect(self._new_local_project)

        # Remote mode
        self._remote_config.connection_changed.connect(self._on_remote_connection_changed)
        self._btn_browse_remote.clicked.connect(self._browse_remote)
        self._btn_new_remote.clicked.connect(self._new_remote_project)

        # Dialog buttons
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_open.clicked.connect(self._open_project)

    def _set_mode(self, mode: str):
        """Set the current mode."""
        is_local = mode == "local"
        self._btn_local.setChecked(is_local)
        self._btn_remote.setChecked(not is_local)
        self._stack.setCurrentIndex(0 if is_local else 1)

    def _browse_local(self):
        """Browse for local project directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Project Directory",
            os.path.expanduser("~")
        )
        if path:
            self._local_path.setText(path)

    def _new_local_project(self):
        """Create new local project."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Directory for New Project",
            os.path.expanduser("~")
        )
        if path:
            # Create nml directory
            nml_dir = os.path.join(path, "nml")
            os.makedirs(nml_dir, exist_ok=True)
            self._local_path.setText(path)

    def _on_remote_connection_changed(self, connected: bool):
        """Handle remote connection state change."""
        self._remote_path.setEnabled(connected)
        self._btn_browse_remote.setEnabled(connected)
        self._btn_new_remote.setEnabled(connected)

    def _browse_remote(self):
        """Browse remote server for project directory."""
        ssh_manager = self._remote_config.get_ssh_manager()
        if not ssh_manager or not ssh_manager.is_connected:
            return

        # Get home directory as starting point
        try:
            home = ssh_manager._get_home_dir()
        except Exception:
            home = "/"

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Remote Project Directory")
        dialog.resize(500, 400)

        layout = QVBoxLayout(dialog)
        browser = RemoteFileBrowser(ssh_manager, home, dialog, select_dirs=True)
        layout.addWidget(browser)

        selected = [None]

        def on_selected(path):
            selected[0] = path
            dialog.accept()

        browser.file_selected.connect(on_selected)

        if dialog.exec() and selected[0]:
            self._remote_path.setText(selected[0])

    def _new_remote_project(self):
        """Create new remote project."""
        ssh_manager = self._remote_config.get_ssh_manager()
        if not ssh_manager or not ssh_manager.is_connected:
            return

        # First browse for parent directory
        self._browse_remote()

        if self._remote_path.text():
            path = self._remote_path.text()
            # Create nml directory on remote
            nml_path = f"{path.rstrip('/')}/nml"
            ssh_manager.execute(f"mkdir -p '{nml_path}'", timeout=10)

    def _open_project(self):
        """Open the selected project."""
        if self._btn_local.isChecked():
            self._open_local_project()
        else:
            self._open_remote_project()

    def _open_local_project(self):
        """Open local project."""
        path = self._local_path.text().strip()
        if not path:
            QMessageBox.warning(self, "Error", "Please select a project directory.")
            return

        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Directory does not exist.")
            return

        # Check for nml directory
        nml_dir = os.path.join(path, "nml")
        if not os.path.isdir(nml_dir):
            reply = QMessageBox.question(
                self, "Create Project",
                "No nml/ directory found. Create new project?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                os.makedirs(nml_dir, exist_ok=True)
            else:
                return

        # Create storage
        self._storage = LocalStorage(path)
        self._project_name = os.path.basename(path)

        self.accept()

    def _open_remote_project(self):
        """Open remote project."""
        ssh_manager = self._remote_config.get_ssh_manager()
        if not ssh_manager or not ssh_manager.is_connected:
            QMessageBox.warning(self, "Error", "Please connect to remote server first.")
            return

        path = self._remote_path.text().strip()
        if not path:
            QMessageBox.warning(self, "Error", "Please select a remote project directory.")
            return

        # Check for nml directory
        stdout, stderr, exit_code = ssh_manager.execute(
            f"test -d '{path}/nml' && echo 'exists'", timeout=10
        )

        if 'exists' not in stdout:
            reply = QMessageBox.question(
                self, "Create Project",
                "No nml/ directory found. Create new project?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                ssh_manager.execute(f"mkdir -p '{path}/nml'", timeout=10)
            else:
                return

        # Create sync engine and storage
        sync_engine = SyncEngine(ssh_manager, path)
        self._storage = RemoteStorage(path, sync_engine)
        self._project_name = path.rstrip('/').split('/')[-1]

        # Start background sync
        sync_engine.start_background_sync()

        self.accept()

    def get_storage(self) -> Optional[ProjectStorage]:
        """Get the created storage instance."""
        return self._storage

    def get_project_name(self) -> str:
        """Get the project name."""
        return self._project_name

    def get_ssh_manager(self):
        """Get SSH manager if in remote mode."""
        if self._btn_remote.isChecked():
            return self._remote_config.get_ssh_manager()
        return None
```

**Step 2: Commit**

```bash
mkdir -p ui/dialogs
git add ui/dialogs/project_selector.py
git commit -m "$(cat <<'EOF'
feat: add ProjectSelectorDialog for startup project selection

Provides unified dialog for opening local or remote projects.
Creates appropriate storage instance based on selection.
EOF
)"
```

---

## Task 7: Create Connection Manager for Saved Connections

**Files:**
- Create: `core/connection_manager.py`
- Test: `tests/test_connection_manager.py`

**Step 1: Write the failing test**

```python
# tests/test_connection_manager.py
import pytest
import os
from core.connection_manager import ConnectionManager

def test_save_and_load_connection(tmp_path):
    """Test saving and loading a connection."""
    config_path = tmp_path / "connections.yaml"
    manager = ConnectionManager(str(config_path))

    manager.save_connection(
        name="Test Server",
        host="user@example.com",
        auth_type="key",
        key_file="~/.ssh/id_rsa"
    )

    connections = manager.list_connections()
    assert len(connections) == 1
    assert connections[0]["name"] == "Test Server"
    assert connections[0]["host"] == "user@example.com"

def test_delete_connection(tmp_path):
    """Test deleting a connection."""
    config_path = tmp_path / "connections.yaml"
    manager = ConnectionManager(str(config_path))

    manager.save_connection(name="Server1", host="user@server1.com")
    manager.save_connection(name="Server2", host="user@server2.com")

    manager.delete_connection("Server1")

    connections = manager.list_connections()
    assert len(connections) == 1
    assert connections[0]["name"] == "Server2"

def test_update_connection(tmp_path):
    """Test updating an existing connection."""
    config_path = tmp_path / "connections.yaml"
    manager = ConnectionManager(str(config_path))

    manager.save_connection(name="Server", host="old@host.com")
    manager.save_connection(name="Server", host="new@host.com")

    connections = manager.list_connections()
    assert len(connections) == 1
    assert connections[0]["host"] == "new@host.com"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_connection_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core.connection_manager'"

**Step 3: Write minimal implementation**

```python
# core/connection_manager.py
# -*- coding: utf-8 -*-
"""
SSH connection configuration manager.

Saves and loads connection profiles from ~/.openbench_wizard/connections.yaml
"""

import os
from typing import Dict, List, Optional, Any
from pathlib import Path

import yaml


class ConnectionManager:
    """Manages saved SSH connection profiles."""

    DEFAULT_PATH = os.path.expanduser("~/.openbench_wizard/connections.yaml")

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize connection manager.

        Args:
            config_path: Path to connections config file.
                        Defaults to ~/.openbench_wizard/connections.yaml
        """
        self._config_path = config_path or self.DEFAULT_PATH
        self._connections: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Load connections from file."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                self._connections = data.get("connections", [])
            except Exception:
                self._connections = []
        else:
            self._connections = []

    def _save(self):
        """Save connections to file."""
        # Ensure directory exists
        dir_path = os.path.dirname(self._config_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        data = {"connections": self._connections}
        with open(self._config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def list_connections(self) -> List[Dict[str, Any]]:
        """Get list of saved connections."""
        return list(self._connections)

    def get_connection(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a connection by name.

        Args:
            name: Connection name

        Returns:
            Connection dict or None if not found
        """
        for conn in self._connections:
            if conn.get("name") == name:
                return dict(conn)
        return None

    def save_connection(
        self,
        name: str,
        host: str,
        auth_type: str = "key",
        key_file: Optional[str] = None,
        jump_node: Optional[str] = None,
        **kwargs
    ):
        """
        Save or update a connection.

        Args:
            name: Display name for connection
            host: Host string (user@host:port)
            auth_type: "key" or "password"
            key_file: Path to SSH key file
            jump_node: Optional jump node host string
            **kwargs: Additional connection parameters
        """
        conn = {
            "name": name,
            "host": host,
            "auth_type": auth_type,
        }

        if key_file:
            conn["key_file"] = key_file
        if jump_node:
            conn["jump_node"] = jump_node

        conn.update(kwargs)

        # Update existing or add new
        for i, existing in enumerate(self._connections):
            if existing.get("name") == name:
                self._connections[i] = conn
                self._save()
                return

        self._connections.append(conn)
        self._save()

    def delete_connection(self, name: str) -> bool:
        """
        Delete a connection.

        Args:
            name: Connection name

        Returns:
            True if deleted, False if not found
        """
        for i, conn in enumerate(self._connections):
            if conn.get("name") == name:
                del self._connections[i]
                self._save()
                return True
        return False
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_connection_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/connection_manager.py tests/test_connection_manager.py
git commit -m "$(cat <<'EOF'
feat: add ConnectionManager for saved SSH profiles

Persists SSH connection configurations to ~/.openbench_wizard/connections.yaml
EOF
)"
```

---

## Task 8: Update WizardController to Use ProjectStorage

**Files:**
- Modify: `ui/wizard_controller.py`

**Step 1: Read current implementation**

The current `WizardController` uses `ConfigManager` for file operations. We need to add `ProjectStorage` support.

**Step 2: Modify WizardController**

Add these changes to `ui/wizard_controller.py`:

```python
# Add import at top
from typing import List, Dict, Any, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from core.storage import ProjectStorage

# In __init__, add:
self._storage: Optional['ProjectStorage'] = None

# Add property:
@property
def storage(self) -> Optional['ProjectStorage']:
    """Get project storage instance."""
    return self._storage

@storage.setter
def storage(self, value: Optional['ProjectStorage']):
    """Set project storage instance."""
    self._storage = value

# Add method:
def is_remote_mode(self) -> bool:
    """Check if using remote storage."""
    from core.storage import RemoteStorage
    return isinstance(self._storage, RemoteStorage)

# Modify sync_namelists to use storage:
def sync_namelists(self):
    """Sync namelists to output directory."""
    if not self._auto_sync_enabled:
        return

    general = self._config.get("general", {})
    basename = general.get("basename", "")
    if not basename:
        return

    # Use storage if available
    if self._storage:
        self._sync_namelists_with_storage()
    else:
        # Fallback to file-based sync
        output_dir = self.get_output_dir()
        openbench_root = self._project_root or get_openbench_root()
        try:
            self._config_manager.sync_namelists(
                self._config, output_dir, openbench_root
            )
            self._config_manager.cleanup_unused_namelists(self._config, output_dir)
            self._save_main_config(output_dir, basename, openbench_root)
        except Exception as e:
            print(f"Warning: Failed to sync namelists: {e}")

def _sync_namelists_with_storage(self):
    """Sync namelists using ProjectStorage."""
    import yaml

    general = self._config.get("general", {})
    basename = general.get("basename", "config")

    # Generate YAML content
    main_content = self._config_manager.generate_main_nml(
        self._config, self._project_root, self.get_output_dir()
    )
    ref_content = self._config_manager.generate_ref_nml(
        self._config, self._project_root, self.get_output_dir()
    )
    sim_content = self._config_manager.generate_sim_nml(
        self._config, self._project_root, self.get_output_dir()
    )

    # Write via storage
    try:
        self._storage.mkdir("nml")
        self._storage.write_file(f"nml/main-{basename}.yaml", main_content)
        self._storage.write_file(f"nml/ref-{basename}.yaml", ref_content)
        self._storage.write_file(f"nml/sim-{basename}.yaml", sim_content)
    except Exception as e:
        print(f"Warning: Failed to sync namelists: {e}")
```

**Step 3: Commit**

```bash
git add ui/wizard_controller.py
git commit -m "$(cat <<'EOF'
feat: add ProjectStorage support to WizardController

Controller now supports storage-based operations for unified
local/remote file handling.
EOF
)"
```

---

## Task 9: Update PathSelector with Autocomplete

**Files:**
- Modify: `ui/widgets/path_selector.py`

**Step 1: Modify PathSelector**

Add autocomplete support to `ui/widgets/path_selector.py`:

```python
# Add imports at top
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from core.storage import ProjectStorage

from ui.widgets.path_completer import PathCompleter

# Modify __init__ to add:
def __init__(
    self,
    mode: str = "directory",
    filter: str = "",
    placeholder: str = "",
    parent=None,
    storage: Optional['ProjectStorage'] = None
):
    # ... existing init code ...

    # Add autocomplete
    self._storage = storage
    self._completer: Optional[PathCompleter] = None
    if storage:
        self._setup_completer(storage)

# Add method:
def _setup_completer(self, storage: 'ProjectStorage'):
    """Setup path autocomplete."""
    self._completer = PathCompleter(storage, self)
    self.line_edit.setCompleter(self._completer)
    self.line_edit.textChanged.connect(self._on_text_for_completion)

def _on_text_for_completion(self, text: str):
    """Trigger completion update."""
    if self._completer:
        self._completer.update_completions(text)

def set_storage(self, storage: Optional['ProjectStorage']):
    """Set storage backend for autocomplete."""
    self._storage = storage
    if storage:
        if not self._completer:
            self._setup_completer(storage)
        else:
            self._completer.set_storage(storage)
    elif self._completer:
        self._completer.set_storage(None)
```

**Step 2: Commit**

```bash
git add ui/widgets/path_selector.py
git commit -m "$(cat <<'EOF'
feat: add storage-backed autocomplete to PathSelector

PathSelector now supports autocomplete from ProjectStorage,
enabling remote path completion.
EOF
)"
```

---

## Task 10: Update MainWindow for New Startup Flow

**Files:**
- Modify: `ui/main_window.py`

**Step 1: Modify MainWindow**

Add project selector integration to `ui/main_window.py`:

```python
# Add import at top
from ui.dialogs.project_selector import ProjectSelectorDialog
from ui.widgets.sync_status import SyncStatusWidget
from core.storage import ProjectStorage, LocalStorage, RemoteStorage
from core.sync_engine import SyncStatus

# Modify __init__:
def __init__(self):
    super().__init__()
    self.setWindowTitle("OpenBench NML Wizard")
    self.setMinimumSize(1200, 800)

    # Initialize controller
    self.controller = WizardController(self)

    # Setup UI first
    self._setup_ui()
    self._connect_signals()
    self._update_navigation()

    # Show project selector on startup
    QTimer.singleShot(100, self._show_project_selector)

# Add method:
def _show_project_selector(self):
    """Show project selector dialog."""
    dialog = ProjectSelectorDialog(self)

    if dialog.exec() == QDialog.Accepted:
        storage = dialog.get_storage()
        project_name = dialog.get_project_name()

        if storage:
            self.controller.storage = storage
            self.controller.project_root = storage.project_dir

            # Setup SSH manager for remote mode
            ssh_manager = dialog.get_ssh_manager()
            if ssh_manager:
                self.controller.ssh_manager = ssh_manager

            # Update sync status widget if remote
            if isinstance(storage, RemoteStorage):
                self._setup_sync_status(storage.sync_engine)

            # Load project if config exists
            self._try_load_project_config()
    else:
        # User cancelled - close application
        self.close()

def _setup_sync_status(self, sync_engine):
    """Setup sync status widget for remote mode."""
    # Add sync status to bottom bar
    if hasattr(self, '_sync_status'):
        self._sync_status.setParent(None)

    self._sync_status = SyncStatusWidget(self)

    # Insert before stretch in nav_bar
    # (Implementation depends on exact layout structure)

    # Connect to sync engine
    def on_status_changed(path, status):
        overall = sync_engine.get_overall_status()
        pending = sync_engine.get_pending_count()
        self._sync_status.set_status(overall, pending)

    sync_engine._on_status_changed = on_status_changed
    self._sync_status.retry_clicked.connect(sync_engine.retry_errors)

def _try_load_project_config(self):
    """Try to load existing project config."""
    storage = self.controller.storage
    if not storage:
        return

    # Look for main config in nml/
    try:
        files = storage.glob("nml/main-*.yaml")
        if files:
            # Load first main config found
            config_path = files[0]
            content = storage.read_file(config_path)
            # Parse and load config
            config = yaml.safe_load(content) or {}
            # ... load into controller ...
    except Exception as e:
        print(f"No existing config found: {e}")
```

**Step 2: Commit**

```bash
git add ui/main_window.py
git commit -m "$(cat <<'EOF'
feat: integrate ProjectSelector into MainWindow startup

Shows project selector dialog on startup, configures storage,
and sets up sync status for remote mode.
EOF
)"
```

---

## Task 11: Update __init__.py Files

**Files:**
- Modify: `core/__init__.py`
- Modify: `ui/widgets/__init__.py`
- Create: `ui/dialogs/__init__.py`

**Step 1: Update core/__init__.py**

```python
# core/__init__.py
from core.storage import ProjectStorage, LocalStorage, RemoteStorage
from core.sync_engine import SyncEngine, SyncStatus
from core.connection_manager import ConnectionManager
```

**Step 2: Update ui/widgets/__init__.py**

```python
# Add to ui/widgets/__init__.py
from ui.widgets.sync_status import SyncStatusWidget
from ui.widgets.path_completer import PathCompleter
```

**Step 3: Create ui/dialogs/__init__.py**

```python
# ui/dialogs/__init__.py
from ui.dialogs.project_selector import ProjectSelectorDialog
```

**Step 4: Commit**

```bash
git add core/__init__.py ui/widgets/__init__.py ui/dialogs/__init__.py
git commit -m "$(cat <<'EOF'
chore: update __init__.py exports for new modules
EOF
)"
```

---

## Task 12: Remove Legacy Remote Mode Code

**Files:**
- Modify: `ui/pages/page_preview.py` - Remove `_export_and_run_remote()` and related code
- Modify: `ui/pages/page_runtime.py` - Simplify to use storage-based approach
- Modify: `core/data_validator.py` - Use storage interface

This task involves removing the `is_remote` conditional branches throughout the codebase now that we have unified storage.

**Step 1: Identify code to remove**

Look for patterns like:
- `if is_remote:`
- `if general.get("execution_mode") == "remote":`
- `_export_and_run_remote`
- `set_skip_validation`

**Step 2: Replace with storage-based code**

For each location, replace with unified storage calls.

**Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: remove legacy remote mode conditional code

Replace is_remote checks with unified ProjectStorage interface.
EOF
)"
```

---

## Summary

This implementation plan provides:

1. **Tasks 1-3**: Core storage abstraction (`ProjectStorage`, `LocalStorage`, `RemoteStorage`, `SyncEngine`)
2. **Tasks 4-6**: UI components (`SyncStatusWidget`, `PathCompleter`, `ProjectSelectorDialog`)
3. **Task 7**: Connection persistence (`ConnectionManager`)
4. **Tasks 8-10**: Integration into existing code (`WizardController`, `PathSelector`, `MainWindow`)
5. **Tasks 11-12**: Cleanup and exports

Each task follows TDD: write failing test, implement, verify, commit.

---

**Plan complete and saved to `docs/plans/2025-12-29-remote-mode-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
