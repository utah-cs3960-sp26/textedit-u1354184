"""Core text editor widget."""

import os

from PyQt6.QtWidgets import QPlainTextEdit, QScrollBar
from PyQt6.QtGui import QFont, QKeyEvent, QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from .large_file_backend import LargeFileBackend, LARGE_FILE_THRESHOLD, WINDOW_LINES


class TextEditor(QPlainTextEdit):
    """A plain text editor with enhanced editing capabilities."""

    modification_changed = pyqtSignal(bool)
    cursor_position_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = None
        self._backend: LargeFileBackend | None = None
        self._win_start = 0
        self._win_end = 0
        self._total_lines = 0
        self._virtual_scrollbar: QScrollBar | None = None
        self._scroll_timer: QTimer | None = None
        self._reloading_window = False
        self._setup_editor()
        self._connect_signals()

    def _setup_editor(self):
        """Configure editor appearance and behavior."""
        font = QFont("Menlo", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def _connect_signals(self):
        """Connect internal signals."""
        self.document().modificationChanged.connect(self.modification_changed.emit)
        self.cursorPositionChanged.connect(self._emit_cursor_position)

    def _emit_cursor_position(self):
        """Emit cursor position as line and column."""
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        if self._backend is not None:
            line += self._win_start
        self.cursor_position_changed.emit(line, col)

    @property
    def file_path(self):
        """Get the file path associated with this editor."""
        return self._file_path

    @file_path.setter
    def file_path(self, path):
        """Set the file path associated with this editor."""
        self._file_path = path

    @property
    def is_modified(self):
        """Check if the document has been modified."""
        return self.document().isModified()

    def set_modified(self, modified: bool):
        """Set the modification state."""
        self.document().setModified(modified)

    def get_display_name(self):
        """Get a display name for this editor tab."""
        if self._file_path:
            from pathlib import Path
            return Path(self._file_path).name
        return "Untitled"

    def is_large_file_mode(self) -> bool:
        """Return True if this editor is using the large-file backend."""
        return self._backend is not None

    @property
    def total_line_count(self) -> int:
        """Total lines: from backend for large files, from document for small."""
        if self._backend is not None:
            return self._total_lines
        return self.document().blockCount()

    def load_from_text(self, text: str, file_path: str, modified: bool = False) -> None:
        """Initialize editor with given text and file path (no disk read)."""
        self.setPlainText(text)
        self._file_path = file_path
        self.document().setModified(modified)

    def load_file(self, file_path: str) -> bool:
        """Load content from a file."""
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            return False

        if file_size >= LARGE_FILE_THRESHOLD:
            return self._load_large_file(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.setPlainText(f.read())
            self._file_path = file_path
            self.document().setModified(False)
            return True
        except (IOError, OSError):
            return False

    def _load_large_file(self, file_path: str) -> bool:
        """Load a large file using the mmap backend."""
        try:
            if self._backend is not None:
                self._backend.close()
            self._backend = LargeFileBackend(file_path)
            self._file_path = file_path
            self._total_lines = self._backend.total_lines

            # Load the first window
            text, self._win_start, self._win_end = self._backend.get_window_text(0)
            self._reloading_window = True
            self.setPlainText(text)
            self._reloading_window = False
            self.document().setModified(False)

            self._install_virtual_scrollbar()
            return True
        except (IOError, OSError):
            self._backend = None
            return False

    def _install_virtual_scrollbar(self):
        """Install a virtual scrollbar that maps to the full file line range."""
        sb = self.verticalScrollBar()
        self._virtual_scrollbar = sb

        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(80)
        self._scroll_timer.timeout.connect(self._on_scroll_debounced)

        sb.setRange(0, max(0, self._total_lines - 1))
        sb.valueChanged.connect(self._on_virtual_scroll)

    def _on_virtual_scroll(self, value):
        """Handle virtual scrollbar movement — debounce window reload."""
        if self._reloading_window:
            return
        # Check if we're near the edge of the loaded window
        margin = WINDOW_LINES // 4
        if value < self._win_start + margin or value > self._win_end - margin:
            self._scroll_timer.start()

    def _on_scroll_debounced(self):
        """Reload the window centered on the current scroll position."""
        if self._backend is None:
            return
        sb = self._virtual_scrollbar
        if sb is None:
            return
        target_line = sb.value()
        self._reload_window(target_line)

    def _flush_edits_to_backend(self):
        """Push the current window's edits back to the backend as a patch."""
        if self._backend is None:
            return
        edited_text = self.toPlainText()
        self._backend.replace_window(self._win_start, self._win_end, edited_text)

    def _reload_window(self, center_line: int):
        """Reload the text window centered on center_line."""
        if self._backend is None:
            return
        self._flush_edits_to_backend()

        text, self._win_start, self._win_end = self._backend.get_window_text(center_line)
        self._reloading_window = True
        self.setPlainText(text)
        self.document().setModified(False)
        self._reloading_window = False

        # Update scrollbar range and position without triggering reload
        sb = self._virtual_scrollbar
        if sb is not None:
            sb.blockSignals(True)
            sb.setRange(0, max(0, self._total_lines - 1))
            sb.setValue(center_line)
            sb.blockSignals(False)

    def save_file(self, file_path: str = None) -> bool:
        """Save content to a file."""
        path = file_path or self._file_path
        if not path:
            return False

        if self._backend is not None:
            return self._save_large_file(path)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            self._file_path = path
            self.document().setModified(False)
            return True
        except (IOError, OSError):
            return False

    def _save_large_file(self, path: str) -> bool:
        """Save a large file via the backend."""
        try:
            self._flush_edits_to_backend()
            self._backend.save_to(path)
            self._file_path = path
            self._total_lines = self._backend.total_lines

            # Reload current window from the new file
            center = (self._win_start + self._win_end) // 2
            text, self._win_start, self._win_end = self._backend.get_window_text(center)
            self._reloading_window = True
            self.setPlainText(text)
            self._reloading_window = False
            self.document().setModified(False)
            return True
        except (IOError, OSError):
            return False

    # --- Large-file find/replace helpers ---

    def count_matches_in_file(self, search: str, case_sensitive: bool,
                              whole_word: bool) -> int:
        """Count matches across the entire large file."""
        if self._backend is None:
            return 0
        return self._backend.count_matches(search, case_sensitive, whole_word)

    def find_next_in_file(self, search: str, case_sensitive: bool,
                          whole_word: bool) -> bool:
        """Find next match in the large file, reloading window if needed."""
        if self._backend is None:
            return False
        byte_off = self._cursor_to_byte_offset()
        result = self._backend.find_next_in_file(
            search, byte_off, case_sensitive, whole_word)
        if result is not None:
            self._jump_to_file_byte(result, len(search))
            return True
        return False

    def find_prev_in_file(self, search: str, case_sensitive: bool,
                          whole_word: bool) -> bool:
        """Find previous match in the large file."""
        if self._backend is None:
            return False
        byte_off = self._cursor_to_byte_offset()
        result = self._backend.find_prev_in_file(
            search, byte_off, case_sensitive, whole_word)
        if result is not None:
            self._jump_to_file_byte(result, len(search))
            return True
        return False

    def replace_all_in_file(self, search: str, replacement: str,
                            case_sensitive: bool, whole_word: bool) -> int:
        """Replace all occurrences in the large file via backend patches."""
        if self._backend is None:
            return 0
        self._flush_edits_to_backend()
        count = self._backend.replace_all(search, replacement,
                                          case_sensitive, whole_word)
        if count > 0:
            # Reload current window to show changes
            center = (self._win_start + self._win_end) // 2
            self._reload_window(center)
            self.document().setModified(True)
        return count

    def _cursor_to_byte_offset(self) -> int:
        """Convert the current cursor position to a file byte offset."""
        if self._backend is None:
            return 0
        cursor = self.textCursor()
        doc_line = cursor.blockNumber()
        file_line = self._win_start + doc_line
        col = cursor.columnNumber()
        line_byte = self._backend.line_to_byte_offset(file_line)
        # Approximate: assume UTF-8 chars ~ 1 byte for ASCII-heavy files
        return line_byte + col

    def _jump_to_file_byte(self, byte_offset: int, select_len: int = 0):
        """Jump to a byte offset in the file, reloading the window if needed."""
        if self._backend is None:
            return
        target_line = self._backend.byte_offset_to_line(byte_offset)

        # Reload window if target is outside current window
        if target_line < self._win_start or target_line >= self._win_end:
            self._reload_window(target_line)

        # Position cursor within the loaded window
        doc_line = target_line - self._win_start
        line_byte = self._backend.line_to_byte_offset(target_line)
        col = byte_offset - line_byte

        block = self.document().findBlockByLineNumber(doc_line)
        if block.isValid():
            pos = block.position() + min(col, block.length() - 1)
            cursor = self.textCursor()
            cursor.setPosition(pos)
            if select_len > 0:
                cursor.setPosition(pos + select_len, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
            self.centerCursor()

    # --- Standard editing operations ---

    def duplicate_line(self):
        """Duplicate the current line or selection."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.clearSelection()
            cursor.insertText(text)
        else:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            line_text = cursor.selectedText()
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertText('\n' + line_text)
        self.setTextCursor(cursor)

    def delete_line(self):
        """Delete the current line."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor)
        if cursor.atEnd():
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self.setTextCursor(cursor)

    def move_line_up(self):
        """Move the current line up."""
        cursor = self.textCursor()
        if cursor.blockNumber() == 0:
            return
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        line_text = cursor.selectedText()
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText(line_text + '\n')
        cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def move_line_down(self):
        """Move the current line down."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        if cursor.atEnd():
            return
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        line_text = cursor.selectedText()
        cursor.removeSelectedText()
        cursor.deleteChar()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertText('\n' + line_text)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def select_word(self):
        """Select the word under cursor."""
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        self.setTextCursor(cursor)

    def select_line(self):
        """Select the current line."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)

    def select_all(self):
        """Select all text."""
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)

    def go_to_line(self, line_number: int):
        """Go to a specific line number."""
        if self._backend is not None:
            # In large-file mode, reload window centered on target line
            self._reload_window(line_number - 1)
            block = self.document().findBlockByLineNumber(
                line_number - 1 - self._win_start)
            if block.isValid():
                cursor = self.textCursor()
                cursor.setPosition(block.position())
                self.setTextCursor(cursor)
                self.centerCursor()
            return

        block = self.document().findBlockByLineNumber(line_number - 1)
        if block.isValid():
            cursor = self.textCursor()
            cursor.setPosition(block.position())
            self.setTextCursor(cursor)
            self.centerCursor()
