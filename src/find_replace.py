"""Find and replace functionality."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QLabel, QCheckBox
)
from PyQt6.QtGui import QTextCursor, QTextDocument
from PyQt6.QtCore import Qt, pyqtSignal


class FindReplaceWidget(QWidget):
    """Widget for find and replace operations."""
    
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._editor = None
        self._last_match_position = -1
        self._setup_ui()
        self._connect_signals()
        self.hide()
    
    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Search text...")
        find_row.addWidget(self.find_input)
        self.find_prev_btn = QPushButton("◀")
        self.find_prev_btn.setFixedWidth(30)
        find_row.addWidget(self.find_prev_btn)
        self.find_next_btn = QPushButton("▶")
        self.find_next_btn.setFixedWidth(30)
        find_row.addWidget(self.find_next_btn)
        self.match_label = QLabel("")
        self.match_label.setFixedWidth(80)
        find_row.addWidget(self.match_label)
        layout.addLayout(find_row)
        
        replace_row = QHBoxLayout()
        replace_row.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        replace_row.addWidget(self.replace_input)
        self.replace_btn = QPushButton("Replace")
        replace_row.addWidget(self.replace_btn)
        self.replace_all_btn = QPushButton("Replace All")
        replace_row.addWidget(self.replace_all_btn)
        layout.addLayout(replace_row)
        
        options_row = QHBoxLayout()
        self.case_sensitive_cb = QCheckBox("Case Sensitive")
        options_row.addWidget(self.case_sensitive_cb)
        self.whole_word_cb = QCheckBox("Whole Word")
        options_row.addWidget(self.whole_word_cb)
        options_row.addStretch()
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedWidth(30)
        options_row.addWidget(self.close_btn)
        layout.addLayout(options_row)
    
    def _connect_signals(self):
        """Connect button signals."""
        self.find_next_btn.clicked.connect(self.find_next)
        self.find_prev_btn.clicked.connect(self.find_previous)
        self.replace_btn.clicked.connect(self.replace)
        self.replace_all_btn.clicked.connect(self.replace_all)
        self.close_btn.clicked.connect(self._close)
        self.find_input.returnPressed.connect(self.find_next)
        self.find_input.textChanged.connect(self._on_search_text_changed)
    
    def set_editor(self, editor):
        """Set the editor to search in."""
        self._editor = editor
        self._last_match_position = -1
    
    def show_find(self):
        """Show the find bar and focus the input."""
        self.show()
        self.find_input.setFocus()
        self.find_input.selectAll()
        if self._editor:
            cursor = self._editor.textCursor()
            if cursor.hasSelection():
                self.find_input.setText(cursor.selectedText())
    
    def _close(self):
        """Close the find/replace bar."""
        self.hide()
        self.closed.emit()
        if self._editor:
            self._editor.setFocus()
    
    def _on_search_text_changed(self, text):
        """Handle search text changes."""
        self._last_match_position = -1
        self._update_match_count()
        # Automatically find first match when text changes
        if text:
            # Move cursor to start of document to find first occurrence
            if self._editor:
                cursor = QTextCursor(self._editor.document())
                self._editor.setTextCursor(cursor)
                self.find_next()
    
    def _get_find_flags(self):
        """Get the find flags based on options."""
        flags = QTextDocument.FindFlag(0)
        if self.case_sensitive_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_word_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags
    
    def _update_match_count(self):
        """Update the match count label."""
        if not self._editor or not self.find_input.text():
            self.match_label.setText("")
            return
        
        text = self.find_input.text()
        document = self._editor.document()
        flags = self._get_find_flags()
        
        count = 0
        cursor = QTextCursor(document)
        while True:
            cursor = document.find(text, cursor, flags)
            if cursor.isNull():
                break
            count += 1
        
        self.match_label.setText(f"{count} matches")
    
    def find_next(self):
        """Find the next occurrence."""
        if not self._editor or not self.find_input.text():
            return False
        
        text = self.find_input.text()
        flags = self._get_find_flags()
        
        cursor = self._editor.textCursor()
        found = self._editor.document().find(text, cursor, flags)
        
        if found.isNull():
            cursor = QTextCursor(self._editor.document())
            found = self._editor.document().find(text, cursor, flags)
        
        if not found.isNull():
            self._editor.setTextCursor(found)
            self._last_match_position = found.position()
            return True
        return False
    
    def find_previous(self):
        """Find the previous occurrence."""
        if not self._editor or not self.find_input.text():
            return False
        
        text = self.find_input.text()
        flags = self._get_find_flags() | QTextDocument.FindFlag.FindBackward
        
        cursor = self._editor.textCursor()
        found = self._editor.document().find(text, cursor, flags)
        
        if found.isNull():
            cursor = QTextCursor(self._editor.document())
            cursor.movePosition(QTextCursor.MoveOperation.End)
            found = self._editor.document().find(text, cursor, flags)
        
        if not found.isNull():
            self._editor.setTextCursor(found)
            self._last_match_position = found.position()
            return True
        return False
    
    def replace(self):
        """Replace the current selection if it matches."""
        if not self._editor or not self.find_input.text():
            return False
        
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            search = self.find_input.text()
            
            if self.case_sensitive_cb.isChecked():
                matches = selected == search
            else:
                matches = selected.lower() == search.lower()
            
            if matches:
                cursor.insertText(self.replace_input.text())
                self._update_match_count()
        
        return self.find_next()
    
    def replace_all(self):
        """Replace all occurrences."""
        if not self._editor or not self.find_input.text():
            return 0
        
        text = self.find_input.text()
        replacement = self.replace_input.text()
        flags = self._get_find_flags()
        
        cursor = QTextCursor(self._editor.document())
        cursor.beginEditBlock()
        
        count = 0
        while True:
            found = self._editor.document().find(text, cursor, flags)
            if found.isNull():
                break
            found.insertText(replacement)
            cursor = found
            count += 1
        
        cursor.endEditBlock()
        self._update_match_count()
        return count
    
    def keyPressEvent(self, event):
        """Handle key events."""
        if event.key() == Qt.Key.Key_Escape:
            self._close()
        else:
            super().keyPressEvent(event)
