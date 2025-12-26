# Remote Execution Feature Design

## Overview

Add remote server execution capability to OpenBench Wizard, allowing users to configure evaluations locally and run them on remote HPC servers via SSH.

## Use Case

- **Local GUI → Remote Execution**: Configure on local machine, execute on remote server
- **HPC Cluster Support**: Login node → Compute node (multi-hop SSH)
- **Real-time Monitoring**: Stream logs back to local GUI

## UI Design

### Runtime Environment Section (General Settings)

Add execution mode toggle:

```
Execution Mode:  ○ Local  ○ Remote
```

When Remote is selected, show:

```
┌─ Remote Server ─────────────────────────────────┐
│ Host:     [user@192.168.1.100    ] [Test]      │
│ Password: [••••••••              ] ☑ Save      │
│ Auth:     ○ Password  ○ SSH Key [Browse...]    │
│ Status:   🔴 Not connected                      │
└─────────────────────────────────────────────────┘

┌─ Compute Node (Optional) ───────────────────────┐
│ ☑ Run on compute node (jump from main server)  │
│                                                 │
│ Node:     [node110              ]               │
│                                                 │
│ Auth:     ○ None (internal trust)  ← default   │
│           ○ Password  [••••••••    ]            │
│           ○ SSH Key   [Browse...]               │
└─────────────────────────────────────────────────┘

┌─ Remote Python Environment ─────────────────────┐
│ Python:   [/home/user/miniconda3/bin/python ▼] │
│           [Detect] [Refresh]                    │
│ Conda:    [(Not using conda environment)    ▼] │
│ OpenBench:[/home/user/OpenBench             🔍]│
│           [Install OpenBench...]                │
└─────────────────────────────────────────────────┘
```

## Architecture

### SSH Manager (`core/ssh_manager.py`)

```python
class SSHManager:
    """Manage SSH connections, file transfer, and remote command execution"""

    # Connection management
    connect(host, user, password=None, key_file=None)
    connect_with_jump(main_host, jump_host, ...)
    disconnect()
    test_connection() -> bool

    # Environment detection
    detect_python_interpreters() -> List[str]
    detect_conda_envs() -> List[tuple]
    check_openbench_installed() -> Optional[str]

    # File transfer
    upload_file(local_path, remote_path)
    upload_directory(local_dir, remote_dir)
    download_file(remote_path, local_path)

    # Command execution
    execute(command) -> (stdout, stderr, exit_code)
    execute_stream(command, callback) -> generator  # Real-time output
```

### Connection Management

- Maintain session after successful connection to avoid repeated authentication
- Support auto-reconnect on network interruption
- Configurable connection timeout (default 30 seconds)

### Multi-hop SSH

- Use paramiko's `Transport.open_channel()` to create tunnel
- Main server connection → Connect to compute node through tunnel
- Two connections managed independently but share transport channel
- Compute nodes often use internal trust (no password required)

## Remote Execution Flow

```
1. Pre-check
   ├── Verify SSH connection is active
   ├── Check remote Python environment is available
   └── Check remote OpenBench path exists

2. File Upload
   ├── Create remote temp directory: ~/openbench_wizard_jobs/<timestamp>/
   ├── Upload main config file: main-xxx.yaml
   ├── Upload sim/ref namelist files
   └── Upload model definition files

3. Execute Task
   ├── If jump server configured, SSH to compute node
   ├── cd to OpenBench directory
   ├── Activate conda environment (if configured)
   └── Execute: python openbench/openbench.py <config_path>

4. Real-time Monitoring
   ├── Continuously read stdout/stderr through SSH channel
   ├── Parse progress info, update local progress bar
   └── Display logs in Run Monitor page in real-time

5. Completion Handling
   ├── Check exit code
   ├── Optional: download result files
   └── Clean up remote temp files (configurable to keep)
```

### Error Handling

- **SSH disconnected**: Attempt reconnect, continue reading logs
- **Task failed**: Keep remote files for debugging, show error message
- **User cancelled**: Send SIGTERM to terminate remote process

## OpenBench Installation Guide

When user clicks **Install OpenBench...** button:

```
┌─ Install OpenBench on Remote Server ────────────┐
│                                                 │
│ Install Location:                               │
│ [/home/user/OpenBench          ] [Browse...]    │
│                                                 │
│ Installation Method:                            │
│ ○ Git Clone (recommended)                       │
│   Repository: [https://github.com/.../OpenBench]│
│                                                 │
│ ○ Upload from Local                             │
│   Local Path: [/Users/.../OpenBench] [Browse...] │
│                                                 │
│ ○ Custom Command                                │
│   [                                           ] │
│                                                 │
│ ☑ Install Python dependencies (pip install -r) │
│                                                 │
│ [Cancel]                      [Install]         │
└─────────────────────────────────────────────────┘
```

### Installation Flow

1. Check if target directory already exists
2. Execute installation command (git clone or upload)
3. Optional: Install dependencies `pip install -r requirements.txt`
4. Verify installation: Check `openbench/openbench.py` exists
5. Auto-fill OpenBench path on success

## Security

### Credential Storage

```python
# Storage location: ~/.openbench_wizard/credentials.json (permission 600)
{
  "servers": {
    "user@192.168.1.100": {
      "auth_type": "password",
      "password": "<encrypted>",  # Encrypted storage
      "jump_node": "node110",
      "jump_auth": "none"
    }
  }
}
```

### Security Measures

- Passwords encrypted using `cryptography.Fernet` symmetric encryption
- Key derived from machine identifier (MAC address + username hash)
- File permission set to 600 (user read/write only)
- Provide **Clear Saved Credentials** button

### When Password Not Saved

- Prompt for password on each connection
- Password kept in memory only, cleared on program exit

### SSH Key Authentication

- Support selecting `~/.ssh/id_rsa` and other common keys
- Support keys with passphrase (prompt for passphrase)

## Configuration Structure

### File Organization

```
output/project_name/
├── nml/
│   ├── main-project.yaml      # OpenBench config (uploaded to remote)
│   ├── sim/
│   ├── ref/
│   └── .wizard.yaml           # Wizard-only config (local only)
```

### main-project.yaml (Clean OpenBench Config)

```yaml
general:
  basename: my_project
  basedir: /path/to/output
  # ... standard OpenBench configuration
```

### .wizard.yaml (Wizard-specific)

```yaml
execution_mode: remote
remote:
  host: user@192.168.1.100
  auth_type: password
  use_jump: true
  jump_node: node110
  jump_auth: none
  python_path: /home/user/miniconda3/bin/python
  conda_env: openbench
  openbench_path: /home/user/OpenBench
  keep_remote_files: false
```

### Load/Save Logic

- Load both files when opening project
- Save to respective files
- `.wizard.yaml` is NOT uploaded to remote server

## Relationship with OpenBench

**No OpenBench code changes required.**

Wizard acts as a "remote execution channel":

```
┌─────────────────┐      SSH        ┌─────────────────┐
│  Local Wizard   │ ───────────────→│  Remote Server  │
│                 │                 │                 │
│ 1. Generate cfg │   Upload cfg    │ OpenBench       │
│ 2. SSH connect  │ ───────────────→│ (unchanged)     │
│ 3. Upload files │                 │                 │
│ 4. Execute cmd  │   python ...    │ Runs normally   │
│ 5. Read logs    │ ←───────────────│ Output logs     │
└─────────────────┘                 └─────────────────┘
```

From OpenBench's perspective:
- Receives config file path
- Executes evaluation normally
- Outputs logs to stdout

Identical to local execution, except:
- Config files uploaded via SFTP instead of local write
- Commands executed via SSH instead of subprocess
- Logs read through SSH channel instead of local pipe

## Code Structure

### New Files

```
openbench-wizard/
├── core/
│   ├── ssh_manager.py        # SSH connection, file transfer, command execution
│   └── remote_runner.py      # Remote task executor
├── ui/
│   ├── widgets/
│   │   └── remote_config.py  # Remote server config UI component
│   └── dialogs/
│       └── install_openbench_dialog.py  # OpenBench installation wizard
```

### Modified Files

```
├── ui/pages/page_general.py      # Add Remote option to Runtime Environment
├── ui/pages/page_run_monitor.py  # Support remote log streaming
├── core/config_manager.py        # Read/write .wizard.yaml
└── requirements.txt              # Add paramiko, cryptography
```

### New Dependencies

```
paramiko>=3.0.0      # SSH connection
cryptography>=41.0   # Password encryption
```
