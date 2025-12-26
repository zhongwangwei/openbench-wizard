# -*- coding: utf-8 -*-
"""
Run and Monitor page with progress dashboard.
"""

import os
import subprocess
import platform

from PySide6.QtWidgets import QMessageBox, QFileDialog

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
        # Remove the trailing stretch added by BasePage so dashboard can expand
        self._remove_trailing_stretch()

    def _remove_trailing_stretch(self):
        """Remove the trailing stretch from content_layout to allow dashboard to expand."""
        count = self.content_layout.count()
        if count > 0:
            item = self.content_layout.itemAt(count - 1)
            if item and item.spacerItem():
                self.content_layout.takeAt(count - 1)

    def _setup_content(self):
        """Setup page content."""
        self.dashboard = ProgressDashboard()
        self.dashboard.stop_requested.connect(self._on_stop)
        self.dashboard.open_output_requested.connect(self._open_output)

        # Add with stretch factor 1 to fill available space
        self.content_layout.addWidget(self.dashboard, 1)

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
        config = self.controller.config
        eval_items = config.get("evaluation_items", {})
        selected = [k for k, v in eval_items.items() if v]
        general = config.get("general", {})

        tasks = []
        for item in selected:
            tasks.append(f"{item} - Evaluation")
            if general.get("comparison"):
                tasks.append(f"{item} - Comparison")
            if general.get("statistics"):
                tasks.append(f"{item} - Statistics")

        self.dashboard.reset()
        self.dashboard.set_tasks(tasks)
        self.dashboard.start_monitoring()

        # Mark first task as running
        if tasks:
            self.dashboard.update_task_status(tasks[0], TaskStatus.RUNNING)

        # Calculate task counts for accurate progress
        num_variables = len(selected)

        # Count reference sources
        ref_data = config.get("ref_data", {})
        ref_def_nml = ref_data.get("def_nml", {})
        num_ref_sources = len([k for k, v in ref_def_nml.items() if v])

        # Count simulation sources
        sim_data = config.get("sim_data", {})
        sim_def_nml = sim_data.get("def_nml", {})
        num_sim_sources = len([k for k, v in sim_def_nml.items() if v])

        # Count metrics and scores
        metrics = config.get("metrics", {})
        num_metrics = len([k for k, v in metrics.items() if v])

        scores = config.get("scores", {})
        num_scores = len([k for k, v in scores.items() if v])

        # Count groupby types
        num_groupby = 0
        if general.get("IGBP_groupby"):
            num_groupby += 1
        if general.get("PFT_groupby"):
            num_groupby += 1
        if general.get("Climate_zone_groupby"):
            num_groupby += 1

        # Count comparisons
        comparisons = config.get("comparisons", {})
        num_comparisons = len([k for k, v in comparisons.items() if v])

        # Get Python path from config
        python_path = general.get("python_path", "")

        # Create and start runner
        self._runner = EvaluationRunner(config_path, python_path, self)
        self._runner.set_task_counts(
            num_variables=num_variables,
            num_ref_sources=num_ref_sources,
            num_sim_sources=num_sim_sources,
            num_metrics=num_metrics,
            num_scores=num_scores,
            num_groupby=num_groupby,
            num_comparisons=num_comparisons,
            do_evaluation=general.get("evaluation", True),
            do_comparison=general.get("comparison", False),
            do_statistics=general.get("statistics", False)
        )
        self._runner.progress_updated.connect(self._on_progress)
        self._runner.log_message.connect(self._on_log)
        self._runner.finished_signal.connect(self._on_finished)
        self._runner.start()

    def _on_progress(self, progress):
        """Handle progress update."""
        self.dashboard.set_progress(int(progress.progress))

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
            # Check if it's an OpenBench not found error
            if "Could not find OpenBench" in message:
                self._prompt_openbench_location()
            else:
                QMessageBox.warning(self, "Failed", message)

    def _prompt_openbench_location(self):
        """Prompt user to select OpenBench directory."""
        reply = QMessageBox.question(
            self,
            "OpenBench Not Found",
            "Could not find the OpenBench directory automatically.\n\n"
            "Would you like to select it manually?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            dir_path = QFileDialog.getExistingDirectory(
                self,
                "Select OpenBench Directory",
                os.path.expanduser("~"),
                QFileDialog.ShowDirsOnly
            )

            if dir_path:
                # Verify it's a valid OpenBench directory
                script_path = os.path.join(dir_path, "openbench", "openbench.py")
                if os.path.exists(script_path):
                    # Save the path
                    self._save_openbench_path(dir_path)
                    QMessageBox.information(
                        self,
                        "Success",
                        f"OpenBench directory saved:\n{dir_path}\n\n"
                        "Please click Run again."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Invalid Directory",
                        f"The selected directory does not contain openbench/openbench.py:\n{dir_path}"
                    )

    def _save_openbench_path(self, path: str):
        """Save OpenBench directory path."""
        try:
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".openbench_wizard")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "config.txt")
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(path)
        except Exception as e:
            print(f"Warning: Could not save OpenBench path: {e}")

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
        output_dir = self.controller.get_output_dir()

        if os.path.exists(output_dir):
            # Cross-platform open folder with error handling
            try:
                if platform.system() == "Windows":
                    os.startfile(output_dir)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", output_dir], check=False)
                else:  # Linux
                    subprocess.run(["xdg-open", output_dir], check=False)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Open Error",
                    f"Could not open directory:\n{output_dir}\n\nError: {str(e)}"
                )
        else:
            QMessageBox.warning(
                self,
                "Directory Not Found",
                f"Output directory does not exist:\n{output_dir}"
            )

    def load_from_config(self):
        """Called when page becomes visible."""
        pass  # Dashboard state is managed separately
