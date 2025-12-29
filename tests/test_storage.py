# tests/test_storage.py
import pytest
from unittest.mock import Mock, MagicMock
from core.storage import ProjectStorage, LocalStorage, RemoteStorage

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


# RemoteStorage tests - using mocked SyncEngine

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


def test_remote_storage_exists():
    """Test RemoteStorage can check if path exists via SyncEngine."""
    sync_engine = Mock()
    sync_engine.exists.side_effect = [True, False]

    storage = RemoteStorage("/remote/project", sync_engine)

    assert storage.exists("exists.yaml") is True
    assert storage.exists("missing.yaml") is False
    assert sync_engine.exists.call_count == 2


def test_remote_storage_glob():
    """Test RemoteStorage can glob files via SyncEngine."""
    sync_engine = Mock()
    sync_engine.glob.return_value = ["nml/main.yaml", "nml/ref.yaml"]

    storage = RemoteStorage("/remote/project", sync_engine)
    matches = storage.glob("nml/*.yaml")

    assert len(matches) == 2
    assert "nml/main.yaml" in matches
    assert "nml/ref.yaml" in matches
    sync_engine.glob.assert_called_once_with("nml/*.yaml")


def test_remote_storage_mkdir():
    """Test RemoteStorage can create directories via SyncEngine."""
    sync_engine = Mock()

    storage = RemoteStorage("/remote/project", sync_engine)
    storage.mkdir("new_dir")

    sync_engine.mkdir.assert_called_once_with("new_dir")


def test_remote_storage_delete():
    """Test RemoteStorage can delete files via SyncEngine."""
    sync_engine = Mock()

    storage = RemoteStorage("/remote/project", sync_engine)
    storage.delete("old_file.yaml")

    sync_engine.delete.assert_called_once_with("old_file.yaml")


def test_remote_storage_sync_engine_property():
    """Test RemoteStorage exposes sync_engine property."""
    sync_engine = Mock()

    storage = RemoteStorage("/remote/project", sync_engine)

    assert storage.sync_engine is sync_engine


def test_remote_storage_project_dir():
    """Test RemoteStorage has correct project_dir."""
    sync_engine = Mock()

    storage = RemoteStorage("/remote/project", sync_engine)

    assert storage.project_dir == "/remote/project"


# Security tests

def test_local_storage_path_traversal_blocked(tmp_path):
    """Test LocalStorage blocks path traversal attempts."""
    storage = LocalStorage(str(tmp_path))

    # Attempt to escape project directory
    with pytest.raises(ValueError, match="Path escapes project directory"):
        storage.read_file("../../../etc/passwd")

    with pytest.raises(ValueError, match="Path escapes project directory"):
        storage.write_file("../../escape.txt", "malicious")

    with pytest.raises(ValueError, match="Path escapes project directory"):
        storage.exists("../outside.txt")


def test_local_storage_delete_nonexistent_raises(tmp_path):
    """Test LocalStorage raises error when deleting non-existent file."""
    storage = LocalStorage(str(tmp_path))

    with pytest.raises(FileNotFoundError, match="Path does not exist"):
        storage.delete("nonexistent.txt")
