# -*- coding: utf-8 -*-
"""
OpenBench evaluation runner with progress tracking.
"""

import os
import sys
import subprocess
import threading
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QObject, Signal, QThread


class RunnerStatus(Enum):
    """Runner status enum."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class RunnerProgress:
    """Progress information."""
    status: RunnerStatus
    progress: float  # 0-100
    current_task: str
    current_variable: str
    current_stage: str
    message: str


class EvaluationRunner(QThread):
    """Thread for running OpenBench evaluation."""

    progress_updated = Signal(object)  # RunnerProgress
    log_message = Signal(str)
    finished_signal = Signal(bool, str)  # success, message

    def __init__(self, config_path: str, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self._stop_requested = False
        self._pause_requested = False
        self._process: Optional[subprocess.Popen] = None

    def run(self):
        """Run the evaluation."""
        try:
            self._emit_progress(
                RunnerStatus.RUNNING,
                0,
                "Initializing",
                "",
                "Starting",
                "Starting OpenBench evaluation..."
            )
            self.log_message.emit("Starting OpenBench evaluation...")

            # Build command
            # Assumes openbench is in PYTHONPATH or installed
            openbench_path = self._find_openbench_script()

            if not openbench_path:
                self.finished_signal.emit(False, "Could not find OpenBench script")
                return

            cmd = [
                sys.executable,
                openbench_path,
                self.config_path
            ]

            self.log_message.emit(f"Running: {' '.join(cmd)}")

            # Determine project root (where openbench directory is)
            config_dir = os.path.dirname(os.path.abspath(self.config_path))
            # Navigate up from nml/nml-yaml to project root
            project_root = os.path.dirname(os.path.dirname(config_dir))
            if not os.path.exists(os.path.join(project_root, "openbench")):
                # Try one level up
                project_root = os.path.dirname(config_dir)
            if not os.path.exists(os.path.join(project_root, "openbench")):
                # Fall back to current working directory
                project_root = os.getcwd()

            self.log_message.emit(f"Working directory: {project_root}")

            # Start process
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=project_root
            )

            # Read output
            progress = 0
            while True:
                if self._stop_requested:
                    self._process.terminate()
                    self._emit_progress(
                        RunnerStatus.STOPPED, progress,
                        "Stopped", "", "", "Evaluation stopped by user"
                    )
                    self.finished_signal.emit(False, "Stopped by user")
                    return

                line = self._process.stdout.readline()
                if not line and self._process.poll() is not None:
                    break

                if line:
                    line = line.strip()
                    self.log_message.emit(line)

                    # Parse progress from log
                    progress, var, stage = self._parse_progress(line, progress)
                    self._emit_progress(
                        RunnerStatus.RUNNING,
                        progress,
                        f"{var} - {stage}" if var else "Processing",
                        var,
                        stage,
                        line
                    )

            # Check result
            return_code = self._process.wait()

            if return_code == 0:
                self._emit_progress(
                    RunnerStatus.COMPLETED, 100,
                    "Complete", "", "", "Evaluation completed successfully"
                )
                self.finished_signal.emit(True, "Evaluation completed successfully")
            else:
                self._emit_progress(
                    RunnerStatus.FAILED, progress,
                    "Failed", "", "", f"Process exited with code {return_code}"
                )
                self.finished_signal.emit(False, f"Process exited with code {return_code}")

        except Exception as e:
            self._emit_progress(
                RunnerStatus.FAILED, 0,
                "Error", "", "", str(e)
            )
            self.finished_signal.emit(False, str(e))

    def _find_openbench_script(self) -> Optional[str]:
        """Find the OpenBench main script."""
        config_dir = os.path.dirname(os.path.abspath(self.config_path))

        # Look for openbench.py in common locations
        possible_paths = [
            # Relative to config file (nml/nml-yaml -> project root -> openbench)
            os.path.join(config_dir, "..", "..", "openbench", "openbench.py"),
            os.path.join(config_dir, "..", "openbench", "openbench.py"),
            # Relative to current working directory
            os.path.join(os.getcwd(), "openbench", "openbench.py"),
            # Absolute fallback
            "openbench/openbench.py",
        ]

        self.log_message.emit(f"Looking for OpenBench script...")
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            self.log_message.emit(f"  Checking: {abs_path}")
            if os.path.exists(abs_path):
                self.log_message.emit(f"  Found: {abs_path}")
                return abs_path

        self.log_message.emit("OpenBench script not found in any expected location")
        return None

    def _parse_progress(self, line: str, current_progress: float) -> tuple:
        """Parse progress from log line."""
        var = ""
        stage = ""

        # Simple parsing - customize based on actual log format
        line_lower = line.lower()

        if "processing" in line_lower:
            # Try to extract variable name
            if "Processing" in line:
                parts = line.split("Processing")
                if len(parts) > 1:
                    var = parts[1].strip().split()[0] if parts[1].strip() else ""

        if "evaluation" in line_lower:
            stage = "Evaluation"
            current_progress = min(current_progress + 2, 95)
        elif "comparison" in line_lower:
            stage = "Comparison"
            current_progress = min(current_progress + 2, 95)
        elif "statistics" in line_lower:
            stage = "Statistics"
            current_progress = min(current_progress + 2, 95)
        elif "complete" in line_lower or "finished" in line_lower:
            current_progress = min(current_progress + 5, 95)

        return current_progress, var, stage

    def _emit_progress(
        self,
        status: RunnerStatus,
        progress: float,
        task: str,
        variable: str,
        stage: str,
        message: str
    ):
        """Emit progress signal."""
        self.progress_updated.emit(RunnerProgress(
            status=status,
            progress=progress,
            current_task=task,
            current_variable=variable,
            current_stage=stage,
            message=message
        ))

    def stop(self):
        """Request stop."""
        self._stop_requested = True
        if self._process:
            self._process.terminate()

    def pause(self):
        """Request pause (not fully implemented - requires process support)."""
        self._pause_requested = True

    def resume(self):
        """Resume from pause."""
        self._pause_requested = False
