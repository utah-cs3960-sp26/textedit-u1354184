"""Tab widget for multi-file support."""

from PyQt6.QtWidgets import QTabWidget, QTabBar, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path

from .editor import TextEditor


class EditorTabWidget(QTabWidget):
    """Tab widget that manages multiple editor instances."""
    
    current_editor_changed = pyqtSignal(object)
    all_tabs_closed = pyqtSignal()
    file_loaded = pyqtSignal()  # Signal when a file is loaded
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._on_current_changed)
        
        self.new_tab()
    
    def _on_current_changed(self, index):
        """Handle tab change."""
        editor = self.widget(index)
        self.current_editor_changed.emit(editor)
    
    def current_editor(self) -> TextEditor:
        """Get the current editor."""
        return self.currentWidget()
    
    def new_tab(self, file_path: str = None) -> TextEditor:
        """Create a new editor tab."""
        editor = TextEditor()
        
        if file_path:
            if editor.load_file(file_path):
                tab_name = Path(file_path).name
            else:
                QMessageBox.warning(
                    self, "Error", 
                    f"Could not open file: {file_path}"
                )
                return None
        else:
            tab_name = "Untitled"
        
        index = self.addTab(editor, tab_name)
        self.setCurrentIndex(index)
        
        editor.modification_changed.connect(
            lambda modified: self._update_tab_title(editor)
        )
        
        return editor
    
    def _update_tab_title(self, editor: TextEditor):
        """Update tab title based on modification state."""
        index = self.indexOf(editor)
        if index == -1:
            return
        
        name = editor.get_display_name()
        if editor.is_modified:
            name = f"● {name}"
        self.setTabText(index, name)
    
    def open_file(self, file_path: str = None) -> TextEditor:
        """Open a file in a new tab or switch to existing tab."""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open File", "", "All Files (*)"
            )
            if not file_path:
                return None
        
        for i in range(self.count()):
            editor = self.widget(i)
            if editor.file_path == file_path:
                self.setCurrentIndex(i)
                self.file_loaded.emit()  # Emit signal when switching to existing file
                return editor
        
        current = self.current_editor()
        if (current and not current.file_path and 
            not current.is_modified and 
            not current.toPlainText()):
            if current.load_file(file_path):
                self._update_tab_title(current)
                self.file_loaded.emit()  # Emit signal after file loaded
                return current
        
        result = self.new_tab(file_path)
        if result:
            self.file_loaded.emit()  # Emit signal after new tab with file
        return result
    
    def save_current(self) -> bool:
        """Save the current file."""
        editor = self.current_editor()
        if not editor:
            return False
        
        if editor.file_path:
            success = editor.save_file()
            if success:
                self._update_tab_title(editor)
            return success
        else:
            return self.save_current_as()
    
    def save_current_as(self) -> bool:
        """Save the current file with a new name."""
        editor = self.current_editor()
        if not editor:
            return False
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "All Files (*)"
        )
        if not file_path:
            return False
        
        success = editor.save_file(file_path)
        if success:
            self._update_tab_title(editor)
        return success
    
    def close_tab(self, index: int) -> bool:
        """Close a tab, prompting to save if modified."""
        editor = self.widget(index)
        if not editor:
            return False
        
        if editor.is_modified:
            name = editor.get_display_name()
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"Save changes to {name}?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return False
            elif reply == QMessageBox.StandardButton.Save:
                self.setCurrentIndex(index)
                if not self.save_current():
                    return False
        
        self.removeTab(index)
        
        if self.count() == 0:
            self.all_tabs_closed.emit()
        
        return True
    
    def close_all_tabs(self) -> bool:
        """Close all tabs."""
        while self.count() > 0:
            if not self.close_tab(0):
                return False
        return True
    
    def next_tab(self):
        """Switch to the next tab."""
        if self.count() > 1:
            next_index = (self.currentIndex() + 1) % self.count()
            self.setCurrentIndex(next_index)
    
    def previous_tab(self):
        """Switch to the previous tab."""
        if self.count() > 1:
            prev_index = (self.currentIndex() - 1) % self.count()
            self.setCurrentIndex(prev_index)
