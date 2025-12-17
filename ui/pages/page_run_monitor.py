# -*- coding: utf-8 -*-
"""
Run and Monitor page with progress dashboard.
"""

import os
import subprocess
import platform

from PySide6.QtWidgets import QMessageBox

from ui.pages.base_page import BasePage
from ui.widgets import ProgressDashboard, TaskStatus
from core.runner import EvaluationRunner, RunnerStatus


class PageRunMonitor(BasePage):
    """Run and Monitor page."""

    PAGE_ID = "run_monitor"
    PAGE_TITLE = "Run & Monitor"
    PAGE_SUBTITLE = "Monitor evaluation progress"

    def __init__(self, controller, parent=None):
        self._runner = None
        super().__init__(controller, parent)

    def _setup_content(self):
        """Setup page content."""
        self.dashboard = ProgressDashboard()
        self.dashboard.pause_requested.connect(self._on_pause)
        self.dashboard.stop_requested.connect(self._on_stop)
        self.dashboard.open_output_requested.connect(self._open_output)

        self.content_layout.addWidget(self.dashboard)

    def start_run(self, config_path: str):
        """Start evaluation run."""
        if self._runner and self._runner.isRunning():
            QMessageBox.warning(
                self,
                "Already Running",
                "An evaluation is already running. Stop it first."
            )
            return

        # Build task list from config
        eval_items = self.controller.config.get("evaluation_items", {})
        selected = [k for k, v in eval_items.items() if v]

        tasks = []
        for item in selected:
            tasks.append(f"{item} - Evaluation")
            if self.controller.config.get("general", {}).get("comparison"):
                tasks.append(f"{item} - Comparison")
            if self.controller.config.get("general", {}).get("statistics"):
                tasks.append(f"{item} - Statistics")

        self.dashboard.reset()
        self.dashboard.set_tasks(tasks)
        self.dashboard.start_monitoring()

        # Mark first task as running
        if tasks:
            self.dashboard.update_task_status(tasks[0], TaskStatus.RUNNING)

        # Create and start runner
        self._runner = EvaluationRunner(config_path, self)
        self._runner.progress_updated.connect(self._on_progress)
        self._runner.log_message.connect(self._on_log)
        self._runner.finished_signal.connect(self._on_finished)
        self._runner.start()

    def _on_progress(self, progress):
        """Handle progress update."""
        self.dashboard.set_progress(int(progress.progress))
        self.dashboard.set_current_task(
            progress.current_variable or "--",
            progress.current_stage or "--"
        )

        # Update task statuses based on progress
        if progress.current_variable and progress.current_stage:
            task_name = f"{progress.current_variable} - {progress.current_stage}"
            self.dashboard.update_task_status(task_name, TaskStatus.RUNNING)

    def _on_log(self, message: str):
        """Handle log message."""
        self.dashboard.append_log(message)

    def _on_finished(self, success: bool, message: str):
        """Handle run completion."""
        self.dashboard.stop_monitoring()

        if success:
            self.dashboard.set_progress(100)
            QMessageBox.information(self, "Complete", message)
        else:
            QMessageBox.warning(self, "Failed", message)

    def _on_pause(self):
        """Handle pause request."""
        if self._runner:
            self._runner.pause()
            self.dashboard.btn_pause.setText("Resume")

    def _on_stop(self):
        """Handle stop request."""
        if self._runner:
            reply = QMessageBox.question(
                self,
                "Confirm Stop",
                "Are you sure you want to stop the evaluation?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._runner.stop()
                self.dashboard.stop_monitoring()

    def _open_output(self):
        """Open output directory."""
        output_dir = self.controller.config.get("general", {}).get("basedir", "./output")
        output_dir = os.path.abspath(output_dir)

        if os.path.exists(output_dir):
            # Cross-platform open folder
            if platform.system() == "Windows":
                os.startfile(output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            else:  # Linux
                subprocess.run(["xdg-open", output_dir])
        else:
            QMessageBox.warning(
                self,
                "Directory Not Found",
                f"Output directory does not exist:\n{output_dir}"
            )

    def load_from_config(self):
        """Called when page becomes visible."""
        pass  # Dashboard state is managed separately
