# ui/widgets/path_completer.py
# -*- coding: utf-8 -*-
"""
Path autocomplete for storage-backed path input.
"""

import os
from typing import Optional, List
from PySide6.QtWidgets import QCompleter
from PySide6.QtCore import Qt, QStringListModel, QTimer

from core.storage import ProjectStorage


class PathCompleterModel(QStringListModel):
    """Model that fetches path completions from storage."""

    def __init__(self, storage: Optional[ProjectStorage] = None, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._cache: dict = {}
        self._base_path = ""

    def set_storage(self, storage: Optional[ProjectStorage]):
        """Set the storage backend."""
        self._storage = storage
        self._cache.clear()

    def update_completions(self, text: str) -> List[str]:
        """
        Update completions for the given text.

        Args:
            text: Current input text

        Returns:
            List of completion suggestions
        """
        if not self._storage or not text:
            self.setStringList([])
            return []

        # Get directory part and prefix
        if '/' in text:
            dir_part = text.rsplit('/', 1)[0]
            prefix = text.rsplit('/', 1)[1] if '/' in text else text
        else:
            dir_part = ""
            prefix = text

        # Check cache
        cache_key = dir_part
        if cache_key not in self._cache:
            try:
                items = self._storage.list_dir(dir_part)
                self._cache[cache_key] = items
            except Exception:
                self._cache[cache_key] = []

        items = self._cache.get(cache_key, [])

        # Filter by prefix and build full paths
        completions = []
        for item in items:
            if item.lower().startswith(prefix.lower()):
                if dir_part:
                    full_path = f"{dir_part}/{item}"
                else:
                    full_path = item
                completions.append(full_path)

        # Sort: directories first, then files
        completions.sort(key=lambda x: (not x.endswith('/'), x.lower()))

        self.setStringList(completions)
        return completions


class PathCompleter(QCompleter):
    """
    Path completer with delayed fetching for storage backends.
    """

    DELAY_MS = 300  # Delay before fetching completions

    def __init__(self, storage: Optional[ProjectStorage] = None, parent=None):
        self._model = PathCompleterModel(storage, parent)
        super().__init__(self._model, parent)

        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.setFilterMode(Qt.MatchStartsWith)

        # Delay timer for remote fetching
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._fetch_completions)
        self._pending_text = ""

    def set_storage(self, storage: Optional[ProjectStorage]):
        """Set the storage backend."""
        self._model.set_storage(storage)

    def update_completions(self, text: str):
        """
        Request completion update for text.

        Uses delayed fetching to avoid excessive remote calls.
        """
        self._pending_text = text
        self._delay_timer.start(self.DELAY_MS)

    def _fetch_completions(self):
        """Fetch completions after delay."""
        self._model.update_completions(self._pending_text)

    def clear_cache(self):
        """Clear the completion cache."""
        self._model._cache.clear()
