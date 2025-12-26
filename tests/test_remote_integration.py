# -*- coding: utf-8 -*-
"""
Integration tests for remote execution functionality.

Tests the complete workflow of remote execution with mocked SSH connections,
ensuring all components work together correctly.
"""

import os
import pytest
import tempfile
import yaml
from unittest.mock import MagicMock, patch, PropertyMock

from core.ssh_manager import SSHManager, SSHConnectionError
from core.credential_manager import CredentialManager
from core.wizard_config import WizardConfigManager
from core.remote_runner import RemoteRunner
from core.runner import RunnerStatus, RunnerProgress


class TestRemoteWorkflowIntegration:
    """Test complete remote execution workflow."""

    def test_full_connection_workflow_with_password(self):
        """Test complete connection workflow using password authentication."""
        with patch('core.ssh_manager.paramiko.SSHClient') as mock_ssh_class:
            # Setup mock
            mock_client = MagicMock()
            mock_ssh_class.return_value = mock_client
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            mock_transport.is_active.return_value = True

            # Create SSH manager and connect
            manager = SSHManager()
            manager.connect("user@192.168.1.100", password="secret123")

            # Verify connection
            assert manager.is_connected

            # Test command execution
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stdout.read.return_value = b"Hello from remote\n"
            mock_stderr.read.return_value = b""
            mock_stdout.channel.recv_exit_status.return_value = 0
            mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            stdout, stderr, exit_code = manager.execute("echo 'Hello from remote'")
            assert stdout == "Hello from remote\n"
            assert exit_code == 0

            # Disconnect
            manager.disconnect()
            assert not manager.is_connected

    def test_full_connection_workflow_with_key(self):
        """Test complete connection workflow using SSH key authentication."""
        with patch('core.ssh_manager.paramiko.SSHClient') as mock_ssh_class:
            mock_client = MagicMock()
            mock_ssh_class.return_value = mock_client
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            mock_transport.is_active.return_value = True

            manager = SSHManager()
            manager.connect("admin@server.example.com:2222", key_file="/home/user/.ssh/id_rsa")

            mock_client.connect.assert_called_once_with(
                hostname="server.example.com",
                port=2222,
                username="admin",
                password=None,
                key_filename="/home/user/.ssh/id_rsa",
                timeout=30,
                allow_agent=False,
                look_for_keys=False
            )
            assert manager.is_connected

    def test_jump_connection_workflow(self):
        """Test complete jump/multi-hop connection workflow."""
        with patch('core.ssh_manager.paramiko.SSHClient') as mock_ssh_class:
            mock_main_client = MagicMock()
            mock_jump_client = MagicMock()
            mock_transport = MagicMock()
            mock_channel = MagicMock()

            # First call returns main client, second returns jump client
            mock_ssh_class.side_effect = [mock_main_client, mock_jump_client]
            mock_main_client.get_transport.return_value = mock_transport
            mock_transport.is_active.return_value = True
            mock_transport.open_channel.return_value = mock_channel

            # Setup jump client transport
            mock_jump_transport = MagicMock()
            mock_jump_transport.is_active.return_value = True
            mock_jump_client.get_transport.return_value = mock_jump_transport

            # Connect to main server
            manager = SSHManager()
            manager.connect("user@gateway.example.com", password="gateway_pass")
            assert manager.is_connected
            assert not manager.is_jump_connected

            # Connect to compute node through jump
            manager.connect_with_jump("compute-node-01")
            assert manager.is_connected
            assert manager.is_jump_connected

            # Execute should use jump client
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stdout.read.return_value = b"output from compute node\n"
            mock_stderr.read.return_value = b""
            mock_stdout.channel.recv_exit_status.return_value = 0
            mock_jump_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            stdout, stderr, exit_code = manager.execute("hostname")
            assert "output from compute node" in stdout
            mock_jump_client.exec_command.assert_called()

            # Disconnect jump first
            manager.disconnect_jump()
            assert not manager.is_jump_connected
            assert manager.is_connected

            # Full disconnect
            manager.disconnect()
            assert not manager.is_connected


class TestCredentialIntegration:
    """Test credential storage and retrieval integration."""

    def test_save_and_retrieve_credentials_for_connection(self):
        """Test saving credentials and using them for connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save credentials
            cred_manager = CredentialManager(config_dir=tmpdir)
            cred_manager.save_credential(
                host="user@192.168.1.100",
                auth_type="password",
                password="secure_password",
                jump_node="node110",
                jump_auth="none"
            )

            # Retrieve and verify
            cred = cred_manager.get_credential("user@192.168.1.100")
            assert cred is not None
            assert cred["auth_type"] == "password"
            assert cred["password"] == "secure_password"
            assert cred["jump_node"] == "node110"
            assert cred["jump_auth"] == "none"

            # Use credentials for connection
            with patch('core.ssh_manager.paramiko.SSHClient') as mock_ssh_class:
                mock_client = MagicMock()
                mock_ssh_class.return_value = mock_client
                mock_transport = MagicMock()
                mock_client.get_transport.return_value = mock_transport
                mock_transport.is_active.return_value = True

                ssh_manager = SSHManager()
                ssh_manager.connect(
                    cred["jump_node"] if cred.get("use_jump") else "user@192.168.1.100",
                    password=cred["password"]
                )
                assert ssh_manager.is_connected

    def test_credential_persistence_across_sessions(self):
        """Test that credentials persist across manager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First session - save credentials
            manager1 = CredentialManager(config_dir=tmpdir)
            manager1.save_credential(
                host="admin@server",
                auth_type="key",
                key_file="/path/to/key"
            )

            # Second session - load credentials
            manager2 = CredentialManager(config_dir=tmpdir)
            cred = manager2.get_credential("admin@server")

            assert cred is not None
            assert cred["auth_type"] == "key"
            assert cred["key_file"] == "/path/to/key"


class TestWizardConfigIntegration:
    """Test wizard configuration integration with remote execution."""

    def test_wizard_config_with_remote_settings(self):
        """Test complete wizard config flow with remote settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Configure remote execution
            remote_config = {
                "host": "user@cluster.example.com",
                "auth_type": "key",
                "key_file": "/home/user/.ssh/cluster_key",
                "use_jump": True,
                "jump_node": "compute-001",
                "jump_auth": "none",
                "python_path": "/opt/python3.10/bin/python",
                "conda_env": "openbench",
                "openbench_path": "/home/user/OpenBench",
            }

            # Set execution mode to remote
            manager.set_execution_mode(tmpdir, "remote")
            manager.set_remote_config(tmpdir, remote_config)

            # Verify settings
            assert manager.is_remote_execution_enabled(tmpdir) is True
            assert manager.get_remote_host(tmpdir) == "user@cluster.example.com"
            assert manager.get_remote_python_path(tmpdir) == "/opt/python3.10/bin/python"
            assert manager.get_remote_openbench_path(tmpdir) == "/home/user/OpenBench"

            loaded_config = manager.get_remote_config(tmpdir)
            assert loaded_config["use_jump"] is True
            assert loaded_config["jump_node"] == "compute-001"
            assert loaded_config["conda_env"] == "openbench"

    def test_switch_between_local_and_remote(self):
        """Test switching between local and remote execution modes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Default is local
            assert manager.get_execution_mode(tmpdir) == "local"
            assert manager.is_remote_execution_enabled(tmpdir) is False

            # Switch to remote
            manager.set_execution_mode(tmpdir, "remote")
            assert manager.get_execution_mode(tmpdir) == "remote"
            assert manager.is_remote_execution_enabled(tmpdir) is True

            # Switch back to local
            manager.set_execution_mode(tmpdir, "local")
            assert manager.get_execution_mode(tmpdir) == "local"
            assert manager.is_remote_execution_enabled(tmpdir) is False


class TestRemoteRunnerIntegration:
    """Test RemoteRunner with mocked SSH."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_remote_runner_initialization(self, mock_ssh_class):
        """Test RemoteRunner initializes correctly with config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock config file
            config_path = os.path.join(tmpdir, "test_config.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({"test": "config"}, f)

            # Setup mock SSH manager
            mock_client = MagicMock()
            mock_ssh_class.return_value = mock_client
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            mock_transport.is_active.return_value = True

            ssh_manager = SSHManager()
            ssh_manager.connect("user@host", password="pass")

            remote_config = {
                "python_path": "/usr/bin/python3",
                "conda_env": "",
                "openbench_path": "/home/user/OpenBench",
            }

            # Create RemoteRunner
            runner = RemoteRunner(config_path, ssh_manager, remote_config)

            assert runner.config_path == config_path
            assert runner._remote_config == remote_config

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_remote_runner_validates_connection(self, mock_ssh_class):
        """Test RemoteRunner validates SSH connection before running."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({"test": "config"}, f)

            # Create unconnected SSH manager
            ssh_manager = SSHManager()
            # Not connected - is_connected should be False

            remote_config = {
                "python_path": "/usr/bin/python3",
                "conda_env": "",
                "openbench_path": "/home/user/OpenBench",
            }

            runner = RemoteRunner(config_path, ssh_manager, remote_config)

            # Track signals
            signals_received = []

            def capture_finished(success, message):
                signals_received.append((success, message))

            runner.finished_signal.connect(capture_finished)

            # Run should fail due to no connection
            runner.run()

            # Should have received a failure signal
            assert len(signals_received) == 1
            assert signals_received[0][0] is False
            assert "SSH connection" in signals_received[0][1]

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_remote_runner_validates_config(self, mock_ssh_class):
        """Test RemoteRunner validates remote configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({"test": "config"}, f)

            # Setup connected SSH manager
            mock_client = MagicMock()
            mock_ssh_class.return_value = mock_client
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            mock_transport.is_active.return_value = True

            ssh_manager = SSHManager()
            ssh_manager.connect("user@host", password="pass")

            # Missing python_path
            remote_config = {
                "python_path": "",
                "conda_env": "",
                "openbench_path": "/home/user/OpenBench",
            }

            runner = RemoteRunner(config_path, ssh_manager, remote_config)

            signals_received = []

            def capture_finished(success, message):
                signals_received.append((success, message))

            runner.finished_signal.connect(capture_finished)

            runner.run()

            assert len(signals_received) == 1
            assert signals_received[0][0] is False
            assert "Python path" in signals_received[0][1]

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_remote_runner_set_task_counts(self, mock_ssh_class):
        """Test RemoteRunner task count configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({"test": "config"}, f)

            mock_client = MagicMock()
            mock_ssh_class.return_value = mock_client

            ssh_manager = SSHManager()
            remote_config = {
                "python_path": "/usr/bin/python3",
                "conda_env": "",
                "openbench_path": "/home/user/OpenBench",
            }

            runner = RemoteRunner(config_path, ssh_manager, remote_config)

            # Set task counts
            runner.set_task_counts(
                num_variables=5,
                num_ref_sources=2,
                num_sim_sources=3,
                num_metrics=4,
                num_scores=2,
                num_groupby=3,
                num_comparisons=2,
                do_evaluation=True,
                do_comparison=True,
                do_statistics=False
            )

            # Verify counts were set
            assert runner._num_variables == 5
            assert runner._num_ref_sources == 2
            assert runner._num_sim_sources == 3
            assert runner._total_tasks > 0


class TestEnvironmentDetectionIntegration:
    """Test remote environment detection workflow."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_full_environment_detection(self, mock_ssh_class):
        """Test complete environment detection workflow."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client
        mock_transport = MagicMock()
        mock_client.get_transport.return_value = mock_transport
        mock_transport.is_active.return_value = True

        # Mock command responses for environment detection
        def exec_side_effect(cmd, timeout=None):
            mock_stdin = MagicMock()
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""

            if "echo $HOME" in cmd:
                mock_stdout.read.return_value = b"/home/testuser\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "which python3" in cmd:
                mock_stdout.read.return_value = b"/usr/bin/python3\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "which python" in cmd and "python3" not in cmd:
                mock_stdout.read.return_value = b"/usr/bin/python\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "miniforge3/bin/conda" in cmd and "test -f" in cmd:
                mock_stdout.read.return_value = b"exists\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "conda env list" in cmd:
                mock_stdout.read.return_value = b"""# conda environments:
#
base                  *  /home/testuser/miniforge3
openbench                /home/testuser/miniforge3/envs/openbench
"""
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "test -f" in cmd and "openbench.py" in cmd:
                mock_stdout.read.return_value = b"exists\n"
                mock_stdout.channel.recv_exit_status.return_value = 0
            else:
                mock_stdout.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 1

            return mock_stdin, mock_stdout, mock_stderr

        mock_client.exec_command.side_effect = exec_side_effect

        # Connect and detect environment
        manager = SSHManager()
        manager.connect("testuser@host", password="pass")

        # Detect Python interpreters
        pythons = manager.detect_python_interpreters()
        assert len(pythons) >= 1
        assert "/usr/bin/python3" in pythons

        # Detect conda environments
        envs = manager.detect_conda_envs()
        assert len(envs) >= 1
        env_names = [e[0] for e in envs]
        assert "base" in env_names or "openbench" in env_names

        # Check OpenBench installation
        is_installed = manager.check_openbench_installed("/home/testuser/OpenBench")
        assert is_installed is True


class TestEndToEndWorkflow:
    """Test end-to-end remote execution workflow."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_complete_remote_execution_workflow(self, mock_ssh_class):
        """Test the complete workflow from config to execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Configure wizard settings
            wizard_manager = WizardConfigManager()
            wizard_manager.set_execution_mode(tmpdir, "remote")
            wizard_manager.set_remote_config(tmpdir, {
                "host": "user@cluster.example.com",
                "auth_type": "password",
                "key_file": "",
                "use_jump": False,
                "jump_node": "",
                "jump_auth": "none",
                "python_path": "/home/user/miniforge3/bin/python",
                "conda_env": "",
                "openbench_path": "/home/user/OpenBench",
            })

            # Step 2: Save credentials
            cred_manager = CredentialManager(config_dir=tmpdir)
            cred_manager.save_credential(
                host="user@cluster.example.com",
                auth_type="password",
                password="cluster_password"
            )

            # Step 3: Verify config
            assert wizard_manager.is_remote_execution_enabled(tmpdir) is True
            remote_config = wizard_manager.get_remote_config(tmpdir)
            assert remote_config["host"] == "user@cluster.example.com"

            # Step 4: Load credentials
            cred = cred_manager.get_credential("user@cluster.example.com")
            assert cred is not None
            assert cred["password"] == "cluster_password"

            # Step 5: Setup SSH connection (mocked)
            mock_client = MagicMock()
            mock_ssh_class.return_value = mock_client
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            mock_transport.is_active.return_value = True

            ssh_manager = SSHManager()
            ssh_manager.connect(remote_config["host"], password=cred["password"])

            assert ssh_manager.is_connected

            # Step 6: Create test config file
            config_path = os.path.join(tmpdir, "openbench_config.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({
                    "General": {"name": "test_evaluation"},
                    "Evaluation": {"variables": ["GPP"]},
                }, f)

            # Step 7: Create runner (would execute remotely)
            runner = RemoteRunner(config_path, ssh_manager, remote_config)
            runner.set_task_counts(
                num_variables=1,
                num_ref_sources=1,
                num_sim_sources=1,
                num_metrics=2,
                num_scores=1,
                num_groupby=0,
                num_comparisons=0,
                do_evaluation=True,
                do_comparison=False,
                do_statistics=False
            )

            assert runner._total_tasks > 0

            # Cleanup
            ssh_manager.disconnect()
            assert not ssh_manager.is_connected


class TestErrorHandlingIntegration:
    """Test error handling across components."""

    def test_connection_failure_propagates_correctly(self):
        """Test that connection failures propagate with proper error messages."""
        with patch('core.ssh_manager.paramiko.SSHClient') as mock_ssh_class:
            mock_client = MagicMock()
            mock_ssh_class.return_value = mock_client
            mock_client.connect.side_effect = Exception("Connection refused")

            manager = SSHManager()

            with pytest.raises(SSHConnectionError) as exc_info:
                manager.connect("user@badhost", password="pass")

            assert "Connection failed" in str(exc_info.value)
            assert not manager.is_connected

    def test_execution_on_disconnected_raises_error(self):
        """Test that executing commands when disconnected raises error."""
        manager = SSHManager()

        with pytest.raises(SSHConnectionError) as exc_info:
            manager.execute("echo hello")

        assert "Not connected" in str(exc_info.value)

    def test_jump_connection_without_main_raises_error(self):
        """Test that jump connection without main connection raises error."""
        manager = SSHManager()

        with pytest.raises(SSHConnectionError) as exc_info:
            manager.connect_with_jump("node110")

        assert "Must connect to main server first" in str(exc_info.value)

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_file_transfer_on_disconnected_raises_error(self, mock_ssh_class):
        """Test that file transfer when disconnected raises error."""
        manager = SSHManager()

        with pytest.raises(SSHConnectionError):
            manager.upload_file("/local/file", "/remote/file")


class TestProgressTrackingIntegration:
    """Test progress tracking in RemoteRunner."""

    @patch('core.ssh_manager.paramiko.SSHClient')
    def test_progress_parsing(self, mock_ssh_class):
        """Test that progress is parsed correctly from log output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({"test": "config"}, f)

            mock_client = MagicMock()
            mock_ssh_class.return_value = mock_client

            ssh_manager = SSHManager()
            remote_config = {
                "python_path": "/usr/bin/python3",
                "conda_env": "",
                "openbench_path": "/home/user/OpenBench",
            }

            runner = RemoteRunner(config_path, ssh_manager, remote_config)
            runner.set_task_counts(
                num_variables=2,
                num_ref_sources=1,
                num_sim_sources=1,
                num_metrics=2,
                num_scores=1,
                num_groupby=0,
                num_comparisons=0,
                do_evaluation=True,
                do_comparison=False,
                do_statistics=False
            )

            # Test progress parsing with sample log lines
            progress, var, stage = runner._parse_progress(
                "Processing GPP variable...",
                5.0
            )
            assert var == "GPP"

            progress, var, stage = runner._parse_progress(
                "Evaluation started for ET",
                progress
            )
            assert stage == "Evaluation"

            progress, var, stage = runner._parse_progress(
                "Done running comparison task",
                progress
            )
            assert "Comparison" in stage or progress > 5.0


class TestConfigurationValidation:
    """Test configuration validation across components."""

    def test_wizard_config_handles_missing_fields(self):
        """Test that wizard config handles missing fields gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WizardConfigManager()

            # Write minimal config
            config_path = os.path.join(tmpdir, ".wizard.yaml")
            with open(config_path, 'w') as f:
                yaml.dump({"execution": {"mode": "remote"}}, f)

            # Load should merge with defaults
            config = manager.load(tmpdir)

            assert config["execution"]["mode"] == "remote"
            assert "remote" in config
            assert config["remote"]["host"] == ""  # Default value
            assert config["remote"]["auth_type"] == "password"  # Default value

    def test_credential_manager_handles_corrupted_file(self):
        """Test that credential manager handles corrupted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write corrupted credentials file
            cred_path = os.path.join(tmpdir, "credentials.json")
            with open(cred_path, 'w') as f:
                f.write("not valid json {{{")

            manager = CredentialManager(config_dir=tmpdir)
            cred = manager.get_credential("any@host")

            # Should return None without crashing
            assert cred is None

    def test_ssh_manager_requires_username(self):
        """Test that SSH manager requires username in host string."""
        manager = SSHManager()

        with pytest.raises(SSHConnectionError) as exc_info:
            with patch('core.ssh_manager.paramiko.SSHClient'):
                manager.connect("192.168.1.100", password="pass")

        assert "Username is required" in str(exc_info.value)
