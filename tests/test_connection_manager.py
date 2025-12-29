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
