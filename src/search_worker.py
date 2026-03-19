"""Background worker thread for large-file search operations."""

import threading

from PyQt6.QtCore import QThread, pyqtSignal


class SearchWorker(QThread):
    """Runs count_matches or replace_all on a background thread.

    Signals
    -------
    count_finished(int)
        Emitted when a count operation completes.
    replace_finished(int)
        Emitted when a replace-all operation completes.
    """

    count_finished = pyqtSignal(int)
    replace_finished = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel = threading.Event()
        self._task = None  # ('count', backend, ...) or ('replace', backend, ...)
        self._backend = None

    # ------------------------------------------------------------------
    # Public API (called from main thread)
    # ------------------------------------------------------------------

    def start_count(self, backend, search, case_sensitive, whole_word):
        """Cancel any running task and start a new count."""
        self._cancel_and_wait()
        self._cancel.clear()
        self._task = ('count', backend, search, case_sensitive, whole_word)
        self._backend = backend
        self.start()

    def start_replace(self, backend, search, replacement, case_sensitive, whole_word):
        """Cancel any running task and start a new replace-all."""
        self._cancel_and_wait()
        self._cancel.clear()
        self._task = ('replace', backend, search, replacement, case_sensitive, whole_word)
        self._backend = backend
        self.start()

    def cancel(self):
        """Request cancellation of the current task."""
        self._cancel.set()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cancel_and_wait(self):
        """Cancel a running task and block until the thread exits."""
        if self.isRunning():
            self._cancel.set()
            self.wait()

    def run(self):
        """Execute the queued task on the worker thread."""
        task = self._task
        if task is None:
            return

        kind = task[0]
        try:
            if kind == 'count':
                _, backend, search, case_sensitive, whole_word = task
                count = backend.count_matches_async(
                    search, case_sensitive, whole_word, self._cancel)
                if not self._cancel.is_set():
                    self.count_finished.emit(count)

            elif kind == 'replace':
                _, backend, search, replacement, case_sensitive, whole_word = task
                count = backend.replace_all_async(
                    search, replacement, case_sensitive, whole_word, self._cancel)
                if not self._cancel.is_set():
                    self.replace_finished.emit(count)
        except Exception:
            # Backend was closed or mmap invalidated — silently drop
            pass
        finally:
            self._task = None
