# -*- coding: utf-8 -*-
"""Tests for Wizard Config Manager."""

import os
import pytest
import tempfile
import yaml

from core.wizard_config import WizardConfigManager


class TestWizardConfigManager:
    """Test WizardConfigManager functionality."""

    def test_get_config_path(self):
        """Test getting the config file path."""
        manager = WizardConfigManager()
        path = manager.get_config_path("/some/project/dir")
        assert path == "/some/project/dir/.wizard.yaml"

    def test_load_returns_defaults_when_file_missing(self):
        """Test that load returns defaults when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()
            config = manager.load(tmpdir)

            assert config["execution"]["mode"] == "local"
            assert config["remote"]["host"] == ""
            assert config["remote"]["auth_type"] == "password"
            assert config["remote"]["use_jump"] is False

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Create test config
            config = {
                "execution": {"mode": "remote"},
                "remote": {
                    "host": "user@192.168.1.100",
                    "auth_type": "key",
                    "key_file": "/path/to/key",
                    "use_jump": True,
                    "jump_node": "node110",
                    "jump_auth": "none",
                    "python_path": "/usr/bin/python3",
                    "conda_env": "openbench",
                    "openbench_path": "/home/user/OpenBench",
                },
                "ui": {
                    "last_tab": 2,
                    "window_geometry": None,
                },
            }

            # Save
            manager.save(tmpdir, config)

            # Verify file exists
            config_path = os.path.join(tmpdir, ".wizard.yaml")
            assert os.path.exists(config_path)

            # Load and verify
            loaded = manager.load(tmpdir)
            assert loaded["execution"]["mode"] == "remote"
            assert loaded["remote"]["host"] == "user@192.168.1.100"
            assert loaded["remote"]["auth_type"] == "key"
            assert loaded["remote"]["use_jump"] is True
            assert loaded["remote"]["jump_node"] == "node110"
            assert loaded["ui"]["last_tab"] == 2

    def test_save_creates_directory(self):
        """Test that save creates the output directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()
            nested_dir = os.path.join(tmpdir, "nested", "project")

            config = {"execution": {"mode": "local"}}
            manager.save(nested_dir, config)

            assert os.path.exists(os.path.join(nested_dir, ".wizard.yaml"))

    def test_exists(self):
        """Test checking if config file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Initially doesn't exist
            assert manager.exists(tmpdir) is False

            # After save, exists
            manager.save(tmpdir, {"execution": {"mode": "local"}})
            assert manager.exists(tmpdir) is True

    def test_delete(self):
        """Test deleting config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Save first
            manager.save(tmpdir, {"execution": {"mode": "local"}})
            assert manager.exists(tmpdir) is True

            # Delete
            result = manager.delete(tmpdir)
            assert result is True
            assert manager.exists(tmpdir) is False

            # Delete again returns False
            result = manager.delete(tmpdir)
            assert result is False

    def test_merge_with_defaults(self):
        """Test that loaded config is merged with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Write a partial config directly
            config_path = os.path.join(tmpdir, ".wizard.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({"execution": {"mode": "remote"}}, f)

            # Load should merge with defaults
            loaded = manager.load(tmpdir)

            # Custom value preserved
            assert loaded["execution"]["mode"] == "remote"

            # Default values filled in
            assert loaded["remote"]["host"] == ""
            assert loaded["remote"]["auth_type"] == "password"
            assert "ui" in loaded

    def test_get_execution_mode(self):
        """Test getting execution mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Default is local
            assert manager.get_execution_mode(tmpdir) == "local"

            # After setting to remote
            manager.save(tmpdir, {"execution": {"mode": "remote"}})
            assert manager.get_execution_mode(tmpdir) == "remote"

    def test_set_execution_mode(self):
        """Test setting execution mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            manager.set_execution_mode(tmpdir, "remote")
            assert manager.get_execution_mode(tmpdir) == "remote"

            manager.set_execution_mode(tmpdir, "local")
            assert manager.get_execution_mode(tmpdir) == "local"

    def test_get_remote_config(self):
        """Test getting remote config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            remote = manager.get_remote_config(tmpdir)
            assert remote["host"] == ""
            assert remote["auth_type"] == "password"

    def test_set_remote_config(self):
        """Test setting remote config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            remote_config = {
                "host": "admin@server.example.com:2222",
                "auth_type": "key",
                "key_file": "/home/user/.ssh/id_ed25519",
                "use_jump": False,
                "jump_node": "",
                "jump_auth": "none",
                "python_path": "/opt/python/bin/python3",
                "conda_env": "",
                "openbench_path": "/opt/openbench",
            }

            manager.set_remote_config(tmpdir, remote_config)

            loaded = manager.get_remote_config(tmpdir)
            assert loaded["host"] == "admin@server.example.com:2222"
            assert loaded["auth_type"] == "key"
            assert loaded["python_path"] == "/opt/python/bin/python3"

    def test_is_remote_execution_enabled(self):
        """Test checking if remote execution is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Default is local
            assert manager.is_remote_execution_enabled(tmpdir) is False

            # After enabling remote
            manager.set_execution_mode(tmpdir, "remote")
            assert manager.is_remote_execution_enabled(tmpdir) is True

    def test_get_remote_host(self):
        """Test getting remote host."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Default empty
            assert manager.get_remote_host(tmpdir) == ""

            # After setting
            manager.set_remote_config(tmpdir, {"host": "user@10.0.0.1"})
            assert manager.get_remote_host(tmpdir) == "user@10.0.0.1"

    def test_get_remote_python_path(self):
        """Test getting remote Python path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Default empty
            assert manager.get_remote_python_path(tmpdir) == ""

            # After setting
            manager.set_remote_config(tmpdir, {"python_path": "/usr/local/bin/python3"})
            assert manager.get_remote_python_path(tmpdir) == "/usr/local/bin/python3"

    def test_get_remote_openbench_path(self):
        """Test getting remote OpenBench path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Default empty
            assert manager.get_remote_openbench_path(tmpdir) == ""

            # After setting
            manager.set_remote_config(tmpdir, {"openbench_path": "/home/user/OpenBench"})
            assert manager.get_remote_openbench_path(tmpdir) == "/home/user/OpenBench"

    def test_handles_invalid_yaml(self):
        """Test handling of invalid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Write invalid YAML
            config_path = os.path.join(tmpdir, ".wizard.yaml")
            with open(config_path, 'w') as f:
                f.write("invalid: yaml: content: [unclosed")

            # Should return defaults without crashing
            config = manager.load(tmpdir)
            assert config["execution"]["mode"] == "local"

    def test_handles_empty_file(self):
        """Test handling of empty config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Write empty file
            config_path = os.path.join(tmpdir, ".wizard.yaml")
            with open(config_path, 'w') as f:
                pass  # Empty file

            # Should return defaults
            config = manager.load(tmpdir)
            assert config["execution"]["mode"] == "local"
            assert "remote" in config

    def test_deep_merge_nested_dicts(self):
        """Test deep merge of nested dictionaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Write config with only some nested values
            config_path = os.path.join(tmpdir, ".wizard.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({
                    "remote": {
                        "host": "user@example.com",
                        # Other remote fields should come from defaults
                    }
                }, f)

            loaded = manager.load(tmpdir)

            # Custom value preserved
            assert loaded["remote"]["host"] == "user@example.com"

            # Default values filled in for missing nested keys
            assert loaded["remote"]["auth_type"] == "password"
            assert loaded["remote"]["use_jump"] is False
            assert loaded["remote"]["python_path"] == ""

            # Other top-level defaults filled in
            assert loaded["execution"]["mode"] == "local"
