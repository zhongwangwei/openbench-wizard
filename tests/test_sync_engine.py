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
