"""Core text editor widget."""

from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtGui import QFont, QKeyEvent, QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal


class TextEditor(QPlainTextEdit):
    """A plain text editor with enhanced editing capabilities."""
    
    modification_changed = pyqtSignal(bool)
    cursor_position_changed = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = None
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
    
    def load_from_text(self, text: str, file_path: str, modified: bool = False) -> None:
        """Initialize editor with given text and file path (no disk read)."""
        self.setPlainText(text)
        self._file_path = file_path
        self.document().setModified(modified)

    def load_file(self, file_path: str) -> bool:
        """Load content from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.setPlainText(f.read())
            self._file_path = file_path
            self.document().setModified(False)
            return True
        except (IOError, OSError) as e:
            return False
    
    def save_file(self, file_path: str = None) -> bool:
        """Save content to a file."""
        path = file_path or self._file_path
        if not path:
            return False
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            self._file_path = path
            self.document().setModified(False)
            return True
        except (IOError, OSError) as e:
            return False
    
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
        block = self.document().findBlockByLineNumber(line_number - 1)
        if block.isValid():
            cursor = self.textCursor()
            cursor.setPosition(block.position())
            self.setTextCursor(cursor)
            self.centerCursor()
