"""Split view container for side-by-side editing."""

from PyQt6.QtWidgets import QSplitter, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

from .tab_widget import EditorTabWidget


class SplitContainer(QWidget):
    """Container that manages split views of editor tabs."""
    
    current_editor_changed = pyqtSignal(object)
    active_tabs_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_tabs = None
        self._closing = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the initial UI with a single tab widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.root_splitter = QSplitter(Qt.Orientation.Horizontal)
        # Make the splitter handle more visible and easier to grab
        self.root_splitter.setHandleWidth(4)
        self.root_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #555;
            }
            QSplitter::handle:hover {
                background-color: #0078d4;
            }
        """)
        layout.addWidget(self.root_splitter)
        
        initial_tabs = self._create_tab_widget()
        self.root_splitter.addWidget(initial_tabs)
        self._set_active_tabs(initial_tabs)
    
    def _create_tab_widget(self) -> EditorTabWidget:
        """Create a new tab widget with connected signals."""
        tabs = EditorTabWidget()
        tabs.current_editor_changed.connect(self._on_editor_changed)
        tabs.all_tabs_closed.connect(lambda: self._on_all_tabs_closed(tabs))
        
        tabs.focusInEvent = lambda e, t=tabs: self._on_tabs_focused(t, e)
        
        return tabs
    
    def _on_tabs_focused(self, tabs: EditorTabWidget, event):
        """Handle focus change to a tab widget."""
        QWidget.focusInEvent(tabs, event)
        self._set_active_tabs(tabs)
    
    def _set_active_tabs(self, tabs: EditorTabWidget):
        """Set the active tab widget."""
        if self._active_tabs == tabs:
            return
        
        if self._active_tabs:
            self._active_tabs.setStyleSheet("")
        
        self._active_tabs = tabs
        self.active_tabs_changed.emit(tabs)
        
        if tabs and tabs.current_editor():
            self.current_editor_changed.emit(tabs.current_editor())
    
    def _on_editor_changed(self, editor):
        """Handle editor change in any tab widget."""
        sender = self.sender()
        if sender == self._active_tabs:
            self.current_editor_changed.emit(editor)
    
    def _on_all_tabs_closed(self, tabs: EditorTabWidget):
        """Handle when all tabs in a widget are closed."""
        if self._closing:
            return
        
        all_tab_widgets = self._get_all_tab_widgets()
        
        if len(all_tab_widgets) == 1:
            tabs.new_tab()
            return
        
        self._remove_tab_widget(tabs)
    
    def _get_all_tab_widgets(self) -> list:
        """Get all tab widgets in the container."""
        return self.findChildren(EditorTabWidget)
    
    def _remove_tab_widget(self, tabs: EditorTabWidget):
        """Remove a tab widget from the split."""
        parent = tabs.parent()
        tabs.setParent(None)
        tabs.deleteLater()
        
        if self._active_tabs == tabs:
            remaining = self._get_all_tab_widgets()
            if remaining:
                self._set_active_tabs(remaining[0])
                remaining[0].setFocus()
        
        self._cleanup_empty_splitters()
    
    def _cleanup_empty_splitters(self):
        """Remove empty splitters and simplify the tree."""
        def cleanup(splitter):
            for i in range(splitter.count() - 1, -1, -1):
                widget = splitter.widget(i)
                if isinstance(widget, QSplitter):
                    cleanup(widget)
                    if widget.count() == 0:
                        widget.setParent(None)
                        widget.deleteLater()
                    elif widget.count() == 1:
                        child = widget.widget(0)
                        child.setParent(splitter)
                        splitter.insertWidget(i, child)
                        widget.setParent(None)
                        widget.deleteLater()
        
        cleanup(self.root_splitter)
    
    def active_tab_widget(self) -> EditorTabWidget:
        """Get the currently active tab widget."""
        return self._active_tabs
    
    def current_editor(self):
        """Get the current editor from the active tab widget."""
        if self._active_tabs:
            return self._active_tabs.current_editor()
        return None
    
    def split_horizontal(self):
        """Split the active tab widget horizontally (side by side)."""
        self._split(Qt.Orientation.Horizontal)
    
    def split_vertical(self):
        """Split the active tab widget vertically (top and bottom)."""
        self._split(Qt.Orientation.Vertical)
    
    def _split(self, orientation: Qt.Orientation):
        """Split the active tab widget in the given orientation."""
        if not self._active_tabs:
            return
        
        current_tabs = self._active_tabs
        parent = current_tabs.parent()
        
        if isinstance(parent, QSplitter) and parent.orientation() == orientation:
            new_tabs = self._create_tab_widget()
            index = parent.indexOf(current_tabs)
            parent.insertWidget(index + 1, new_tabs)
            self._balance_splitter(parent)
        else:
            new_splitter = QSplitter(orientation)
            # Style the new splitter
            new_splitter.setHandleWidth(4)
            new_splitter.setStyleSheet("""
                QSplitter::handle {
                    background-color: #555;
                }
                QSplitter::handle:hover {
                    background-color: #0078d4;
                }
            """)
            
            if isinstance(parent, QSplitter):
                index = parent.indexOf(current_tabs)
                parent.insertWidget(index, new_splitter)
            
            new_splitter.addWidget(current_tabs)
            
            new_tabs = self._create_tab_widget()
            new_splitter.addWidget(new_tabs)
            self._balance_splitter(new_splitter)
        
        new_tabs.setFocus()
        self._set_active_tabs(new_tabs)
    
    def _balance_splitter(self, splitter: QSplitter):
        """Set equal sizes for all widgets in a splitter."""
        count = splitter.count()
        if count > 0:
            size = 1000
            splitter.setSizes([size // count] * count)
    
    def close_split(self):
        """Close the active split pane."""
        if not self._active_tabs:
            return
        
        all_tabs = self._get_all_tab_widgets()
        if len(all_tabs) <= 1:
            return
        
        if self._active_tabs.close_all_tabs():
            pass
    
    def focus_next_split(self):
        """Focus the next split pane."""
        all_tabs = self._get_all_tab_widgets()
        if len(all_tabs) <= 1:
            return
        
        try:
            current_index = all_tabs.index(self._active_tabs)
            next_index = (current_index + 1) % len(all_tabs)
            all_tabs[next_index].setFocus()
            self._set_active_tabs(all_tabs[next_index])
        except ValueError:
            pass
    
    def focus_previous_split(self):
        """Focus the previous split pane."""
        all_tabs = self._get_all_tab_widgets()
        if len(all_tabs) <= 1:
            return
        
        try:
            current_index = all_tabs.index(self._active_tabs)
            prev_index = (current_index - 1) % len(all_tabs)
            all_tabs[prev_index].setFocus()
            self._set_active_tabs(all_tabs[prev_index])
        except ValueError:
            pass
    
    def new_tab(self, file_path=None):
        """Create a new tab in the active tab widget."""
        if self._active_tabs:
            return self._active_tabs.new_tab(file_path)
        return None
    
    def open_file(self, file_path=None):
        """Open a file in the active tab widget."""
        if self._active_tabs:
            return self._active_tabs.open_file(file_path)
        return None
    
    def save_current(self):
        """Save the current file in the active tab widget."""
        if self._active_tabs:
            return self._active_tabs.save_current()
        return False
    
    def save_current_as(self):
        """Save the current file as in the active tab widget."""
        if self._active_tabs:
            return self._active_tabs.save_current_as()
        return False
    
    def close_current_tab(self):
        """Close the current tab in the active tab widget."""
        if self._active_tabs:
            return self._active_tabs.close_tab(self._active_tabs.currentIndex())
        return False
    
    def close_all_tabs(self) -> bool:
        """Close all tabs in all tab widgets."""
        self._closing = True
        try:
            for tabs in self._get_all_tab_widgets():
                if not tabs.close_all_tabs():
                    self._closing = False
                    return False
            return True
        finally:
            self._closing = False
    
    def next_tab(self):
        """Switch to next tab in active tab widget."""
        if self._active_tabs:
            self._active_tabs.next_tab()
    
    def previous_tab(self):
        """Switch to previous tab in active tab widget."""
        if self._active_tabs:
            self._active_tabs.previous_tab()
    
    def open_file_path(self, file_path: str):
        """Open a file by its full path."""
        if self._active_tabs:
            return self._active_tabs.open_file(file_path)
