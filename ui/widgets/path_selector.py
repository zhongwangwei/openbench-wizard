# -*- coding: utf-8 -*-
"""
Path selector widget with browse button and drag-drop support.
"""

import os

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class PathSelector(QWidget):
    """Widget for selecting file or directory paths."""

    path_changed = Signal(str)
    browse_clicked = Signal()  # Emitted when browse button is clicked

    def __init__(
        self,
        mode: str = "directory",
        filter: str = "",
        placeholder: str = "",
        parent=None
    ):
        """
        Initialize PathSelector.

        Args:
            mode: "directory" or "file"
            filter: File filter for file mode (e.g., "YAML Files (*.yaml)")
            placeholder: Placeholder text for the input field
            parent: Parent widget
        """
        super().__init__(parent)
        self.mode = mode
        self.filter = filter or "All Files (*)"
        self._last_dir = os.path.expanduser("~")
        self._custom_browse_handler = None
        self._skip_validation = False  # Skip path existence validation (for remote mode)

        self._setup_ui(placeholder)
        self._connect_signals()

        # Enable drag and drop
        self.setAcceptDrops(True)

    def _setup_ui(self, placeholder: str):
        """Setup the widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Path input
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        layout.addWidget(self.line_edit, 1)

        # Browse button
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setFixedWidth(100)
        layout.addWidget(self.btn_browse)

    def _connect_signals(self):
        """Connect internal signals."""
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        self.line_edit.textChanged.connect(self._on_text_changed)

    def _on_browse_clicked(self):
        """Handle browse button click."""
        # Emit signal first
        self.browse_clicked.emit()

        # If custom handler is set, use it instead
        if self._custom_browse_handler:
            self._custom_browse_handler()
            return

        if self.mode == "directory":
            path = QFileDialog.getExistingDirectory(
                self,
                "Select Directory",
                self._last_dir,
                QFileDialog.ShowDirsOnly
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File",
                self._last_dir,
                self.filter
            )

        if path:
            self._last_dir = os.path.dirname(path) if self.mode == "file" else path
            self.line_edit.setText(path)

    def set_custom_browse_handler(self, handler):
        """Set a custom browse handler function.

        Args:
            handler: Callable that handles the browse action.
                     Set to None to use default file dialog.
        """
        self._custom_browse_handler = handler

    def _on_text_changed(self, text: str):
        """Handle text changes."""
        # Update line edit style based on path validity
        # Skip validation if _skip_validation is True (for remote paths)
        if text and not self._skip_validation:
            exists = os.path.exists(text)
            if self.mode == "directory":
                valid = exists and os.path.isdir(text)
            else:
                valid = exists and os.path.isfile(text)

            if valid:
                self.line_edit.setStyleSheet("")
            else:
                self.line_edit.setStyleSheet("border-color: #e74c3c;")
        else:
            self.line_edit.setStyleSheet("")

        self.path_changed.emit(text)

    def set_skip_validation(self, skip: bool):
        """Set whether to skip path existence validation.

        Use this for remote paths that don't exist locally.

        Args:
            skip: If True, don't validate path existence
        """
        self._skip_validation = skip
        # Re-trigger validation update
        self._on_text_changed(self.line_edit.text())

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if self.mode == "directory":
                    if os.path.isdir(path):
                        event.acceptProposedAction()
                else:
                    if os.path.isfile(path):
                        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.line_edit.setText(path)

    def path(self) -> str:
        """Get current path."""
        return self.line_edit.text()

    def set_path(self, path: str, emit_signal: bool = True):
        """Set current path and update last directory."""
        if not emit_signal:
            self.line_edit.blockSignals(True)
        self.line_edit.setText(path)
        if not emit_signal:
            self.line_edit.blockSignals(False)
        # Update last_dir based on the path
        if path:
            # Resolve relative path
            resolved_path = path
            if path.startswith("./"):
                resolved_path = os.path.join(os.getcwd(), path[2:])
            elif not os.path.isabs(path):
                resolved_path = os.path.join(os.getcwd(), path)

            if os.path.isfile(resolved_path):
                self._last_dir = os.path.dirname(resolved_path)
            elif os.path.isdir(resolved_path):
                self._last_dir = resolved_path
            else:
                # Path doesn't exist, but try to use its directory
                dir_path = os.path.dirname(resolved_path)
                if dir_path and os.path.isdir(dir_path):
                    self._last_dir = dir_path

    def set_last_dir(self, dir_path: str):
        """Set the starting directory for the file dialog."""
        if os.path.isdir(dir_path):
            self._last_dir = dir_path
