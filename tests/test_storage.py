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
