"""Main application window."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QStatusBar,
    QMenuBar, QMenu, QMessageBox, QInputDialog, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QFont

from .split_container import SplitContainer
from .find_replace import FindReplaceWidget
from .multi_file_find import MultiFileFindDialog
from .file_tree import FileTreeWidget


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
        
        # Horizontal splitter for file tree and editor
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # File tree widget (initially hidden)
        self.file_tree = FileTreeWidget()
        self.file_tree.file_selected.connect(self._on_file_selected)
        self.file_tree.setMaximumWidth(300)
        self.file_tree.hide()
        self.main_splitter.addWidget(self.file_tree)
        
        self.split_container = SplitContainer()
        self.main_splitter.addWidget(self.split_container)
        
        self.main_splitter.setSizes([0, 1000])
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
        search_menu.addSeparator()
        self._add_action(search_menu, "Find in &Files...", self._show_multi_file_find, QKeySequence("Ctrl+Shift+F"))
        
        view_menu = menubar.addMenu("&View")
        self._add_action(view_menu, "&Go to Line...", self._go_to_line, QKeySequence("Ctrl+G"))
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
        
        filetree_menu = menubar.addMenu("&FileTree")
        self._add_action(filetree_menu, "&Open FileTree", self._open_filetree)
        self._add_action(filetree_menu, "&Close FileTree", self._close_filetree)
        
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
        self.find_replace.closed.connect(self._on_find_closed)
    
    def _on_active_tabs_changed(self, tabs):
        """Handle active tab widget change."""
        if tabs:
            editor = tabs.current_editor()
            if editor:
                self.find_replace.set_editor(editor)
    
    def _on_editor_changed(self, editor):
        """Handle editor change."""
        if editor:
            self.find_replace.set_editor(editor)
            try:
                editor.cursor_position_changed.disconnect(self._update_cursor_position)
            except:
                pass
            editor.cursor_position_changed.connect(self._update_cursor_position)
            self._update_cursor_position(1, 1)
            self._update_window_title()
    
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
            "• Multi-file find and replace\n"
            "• Line manipulation shortcuts\n"
            "• Cursor position tracking"
        )
    
    def _show_multi_file_find(self):
        """Show the multi-file find dialog."""
        dialog = MultiFileFindDialog(self.split_container, self)
        dialog.exec()
    
    def _open_filetree(self):
        """Open the file tree."""
        self.file_tree.show()
        self.main_splitter.setSizes([250, 1000])
    
    def _close_filetree(self):
        """Close the file tree."""
        self.file_tree.hide()
        self.main_splitter.setSizes([0, 1000])
    
    def _on_file_selected(self, file_path: str):
        """Handle file selection from file tree."""
        self.split_container.open_file_path(file_path)
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.split_container.close_all_tabs():
            event.accept()
        else:
            event.ignore()
