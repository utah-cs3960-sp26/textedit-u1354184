"""Main application window."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QStatusBar,
    QMenuBar, QMenu, QMessageBox, QInputDialog
)
from PyQt6.QtGui import QAction, QKeySequence, QFont
from PyQt6.QtCore import Qt

from .split_container import SplitContainer
from .find_replace import FindReplaceWidget
from .markdown_preview import MarkdownPreview


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TextEdit")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)
        
        self._setup_central_widget()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._connect_signals()
    
    def _setup_central_widget(self):
        """Set up the central widget with splits and find/replace."""
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create splitter for editor and markdown preview
        from PyQt6.QtWidgets import QSplitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.split_container = SplitContainer()
        self.main_splitter.addWidget(self.split_container)
        
        self.markdown_preview = MarkdownPreview()
        # Show by default
        self.main_splitter.addWidget(self.markdown_preview)
        
        # Set initial sizes (60% editor, 40% preview)
        self.main_splitter.setSizes([600, 400])
        
        layout.addWidget(self.main_splitter)
        
        self.find_replace = FindReplaceWidget()
        layout.addWidget(self.find_replace)
        
        self.setCentralWidget(central)
    
    def _setup_menu_bar(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "&New", self.split_container.new_tab, QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Open...", self.split_container.open_file, QKeySequence.StandardKey.Open)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Save", self.split_container.save_current, QKeySequence.StandardKey.Save)
        self._add_action(file_menu, "Save &As...", self.split_container.save_current_as, QKeySequence.StandardKey.SaveAs)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Close Tab", self.split_container.close_current_tab, QKeySequence("Ctrl+W"))
        self._add_action(file_menu, "Close &All", self.split_container.close_all_tabs, QKeySequence("Ctrl+Shift+W"))
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", self.close, QKeySequence.StandardKey.Quit)
        
        edit_menu = menubar.addMenu("&Edit")
        self._add_action(edit_menu, "&Undo", self._undo, QKeySequence.StandardKey.Undo)
        self._add_action(edit_menu, "&Redo", self._redo, QKeySequence.StandardKey.Redo)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Cu&t", self._cut, QKeySequence.StandardKey.Cut)
        self._add_action(edit_menu, "&Copy", self._copy, QKeySequence.StandardKey.Copy)
        self._add_action(edit_menu, "&Paste", self._paste, QKeySequence.StandardKey.Paste)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Select &All", self._select_all, QKeySequence.StandardKey.SelectAll)
        self._add_action(edit_menu, "Select &Word", self._select_word, QKeySequence("Ctrl+D"))
        self._add_action(edit_menu, "Select &Line", self._select_line, QKeySequence("Ctrl+L"))
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Duplicate Line", self._duplicate_line, QKeySequence("Ctrl+Shift+D"))
        self._add_action(edit_menu, "Delete Line", self._delete_line, QKeySequence("Ctrl+Shift+K"))
        self._add_action(edit_menu, "Move Line Up", self._move_line_up, QKeySequence("Alt+Up"))
        self._add_action(edit_menu, "Move Line Down", self._move_line_down, QKeySequence("Alt+Down"))
        
        search_menu = menubar.addMenu("&Search")
        self._add_action(search_menu, "&Find...", self._show_find, QKeySequence.StandardKey.Find)
        self._add_action(search_menu, "Find &Next", self._find_next, QKeySequence("F3"))
        self._add_action(search_menu, "Find &Previous", self._find_previous, QKeySequence("Shift+F3"))
        self._add_action(search_menu, "&Replace...", self._show_find, QKeySequence.StandardKey.Replace)
        
        view_menu = menubar.addMenu("&View")
        self._add_action(view_menu, "&Go to Line...", self._go_to_line, QKeySequence("Ctrl+G"))
        view_menu.addSeparator()
        self.preview_action = self._add_action(view_menu, "&Markdown Preview", self._toggle_markdown_preview, QKeySequence("Ctrl+M"))
        self.preview_action.setCheckable(True)
        view_menu.addSeparator()
        self._add_action(view_menu, "Split &Right", self.split_container.split_horizontal, QKeySequence("Ctrl+\\"))
        self._add_action(view_menu, "Split &Down", self.split_container.split_vertical, QKeySequence("Ctrl+Shift+\\"))
        self._add_action(view_menu, "Close Split", self.split_container.close_split, QKeySequence("Ctrl+Shift+X"))
        view_menu.addSeparator()
        self._add_action(view_menu, "Focus Next Split", self.split_container.focus_next_split, QKeySequence("Ctrl+Alt+Right"))
        self._add_action(view_menu, "Focus Previous Split", self.split_container.focus_previous_split, QKeySequence("Ctrl+Alt+Left"))
        view_menu.addSeparator()
        self._add_action(view_menu, "Next Tab", self.split_container.next_tab, QKeySequence("Ctrl+Tab"))
        self._add_action(view_menu, "Previous Tab", self.split_container.previous_tab, QKeySequence("Ctrl+Shift+Tab"))
        
        help_menu = menubar.addMenu("&Help")
        self._add_action(help_menu, "&About", self._show_about)
    
    def _add_action(self, menu: QMenu, name: str, callback, shortcut=None) -> QAction:
        """Add an action to a menu."""
        action = QAction(name, self)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)
        menu.addAction(action)
        return action
    
    def _setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _connect_signals(self):
        """Connect signals."""
        self.split_container.current_editor_changed.connect(self._on_editor_changed)
        self.split_container.active_tabs_changed.connect(self._on_active_tabs_changed)
        self.split_container.file_loaded.connect(self._on_file_loaded)
        self.find_replace.closed.connect(self._on_find_closed)
        # Set initial preview state
        self.preview_action.setChecked(True)
        # Update preview for initial editor with delay
        from PyQt6.QtCore import QTimer
        def update_initial():
            editor = self.split_container.current_editor()
            if editor:
                self.markdown_preview.set_editor(editor)
                self._update_markdown_preview()
        QTimer.singleShot(100, update_initial)
    
    def _on_active_tabs_changed(self, tabs):
        """Handle active tab widget change."""
        if tabs:
            editor = tabs.current_editor()
            if editor:
                self.find_replace.set_editor(editor)
                self.markdown_preview.set_editor(editor)
                # Use QTimer to ensure preview updates after UI is ready
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(10, self._update_markdown_preview)
    
    def _on_file_loaded(self):
        """Handle file loaded signal - force preview refresh."""
        from PyQt6.QtCore import QTimer
        # Force a preview update when a file is loaded
        def refresh_preview():
            editor = self.split_container.current_editor()
            if editor:
                self.markdown_preview.set_editor(editor)
                self._update_markdown_preview()
        QTimer.singleShot(100, refresh_preview)
    
    def _on_editor_changed(self, editor):
        """Handle editor change."""
        if editor:
            self.find_replace.set_editor(editor)
            self.markdown_preview.set_editor(editor)
            try:
                editor.cursor_position_changed.disconnect(self._update_cursor_position)
            except:
                pass
            try:
                editor.textChanged.disconnect(self._update_markdown_preview)
            except:
                pass
            editor.cursor_position_changed.connect(self._update_cursor_position)
            editor.textChanged.connect(self._update_markdown_preview)
            self._update_cursor_position(1, 1)
            self._update_window_title()
            # Use QTimer to ensure preview updates after UI is ready
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(10, self._update_markdown_preview)
    
    def _update_cursor_position(self, line: int, col: int):
        """Update status bar with cursor position."""
        self.status_bar.showMessage(f"Line {line}, Column {col}")
    
    def _update_window_title(self):
        """Update window title."""
        editor = self.split_container.current_editor()
        if editor and editor.file_path:
            self.setWindowTitle(f"{editor.get_display_name()} - TextEdit")
        else:
            self.setWindowTitle("TextEdit")
    
    def _undo(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.undo()
    
    def _redo(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.redo()
    
    def _cut(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.cut()
    
    def _copy(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.copy()
    
    def _paste(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.paste()
    
    def _select_all(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.select_all()
    
    def _select_word(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.select_word()
    
    def _select_line(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.select_line()
    
    def _duplicate_line(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.duplicate_line()
    
    def _delete_line(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.delete_line()
    
    def _move_line_up(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.move_line_up()
    
    def _move_line_down(self):
        editor = self.split_container.current_editor()
        if editor:
            editor.move_line_down()
    
    def _toggle_markdown_preview(self):
        """Toggle markdown preview visibility."""
        if self.markdown_preview.isVisible():
            self.markdown_preview.hide()
            self.preview_action.setChecked(False)
        else:
            self.markdown_preview.show()
            self.preview_action.setChecked(True)
            # Force update after showing with a small delay
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, self._update_markdown_preview)
    
    def _update_markdown_preview(self):
        """Update markdown preview with current editor content."""
        editor = self.split_container.current_editor()
        if editor:
            # Always update if we have an editor - visibility is managed separately
            self.markdown_preview.update_preview(editor.toPlainText())
    
    def _show_find(self):
        """Show the find/replace bar."""
        self.find_replace.set_editor(self.split_container.current_editor())
        self.find_replace.show_find()
    
    def _on_find_closed(self):
        """Handle find bar closed."""
        editor = self.split_container.current_editor()
        if editor:
            editor.setFocus()
    
    def _find_next(self):
        if self.find_replace.isVisible():
            self.find_replace.find_next()
        else:
            self._show_find()
    
    def _find_previous(self):
        if self.find_replace.isVisible():
            self.find_replace.find_previous()
        else:
            self._show_find()
    
    def _go_to_line(self):
        """Show go to line dialog."""
        editor = self.split_container.current_editor()
        if not editor:
            return
        
        max_line = editor.document().blockCount()
        line, ok = QInputDialog.getInt(
            self, "Go to Line",
            f"Line number (1-{max_line}):",
            1, 1, max_line
        )
        if ok:
            editor.go_to_line(line)
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About TextEdit",
            "TextEdit\n\n"
            "A simple cross-platform text editor built with PyQt6.\n\n"
            "Features:\n"
            "• Multi-file editing with tabs\n"
            "• Split views (horizontal and vertical)\n"
            "• Find and replace\n"
            "• Markdown preview\n"
            "• Line manipulation shortcuts\n"
            "• Cursor position tracking"
        )
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.split_container.close_all_tabs():
            event.accept()
        else:
            event.ignore()
