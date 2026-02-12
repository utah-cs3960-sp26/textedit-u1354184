"""File tree widget for browsing and opening files."""

from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal


class FileTreeWidget(QWidget):
    """Widget for browsing files in a tree structure."""
    
    file_selected = pyqtSignal(str)  # Emits file path when file is selected
    
    # Supported file extensions for the editor
    SUPPORTED_EXTENSIONS = {
        # Code
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
        '.rb', '.go', '.rs', '.php', '.swift', '.kt', '.scala',
        # Web
        '.html', '.css', '.scss', '.sass', '.less',
        # Config/Data
        '.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.conf', '.properties',
        # Text
        '.txt', '.md', '.markdown', '.rst', '.tex',
        # Shell
        '.sh', '.bash', '.zsh', '.fish',
        # Other
        '.sql', '.csv', '.log'
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_root = Path.home()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(False)
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabel("Files")
        layout.addWidget(self.tree)
        
        self.load_directory(self.current_root)
    
    def _connect_signals(self):
        """Connect signals."""
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemExpanded.connect(self._on_item_expanded)
    
    def load_directory(self, path: Path):
        """Load a directory into the tree."""
        self.tree.clear()
        self.current_root = path
        self._populate_tree(None, path)
    
    def _is_supported_file(self, path: Path) -> bool:
        """Check if file is supported by the editor."""
        if path.is_dir():
            return True
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def _populate_tree(self, parent_item, directory: Path):
        """Recursively populate tree with files and folders."""
        try:
            items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item_path in items:
                # Skip hidden files
                if item_path.name.startswith('.'):
                    continue
                
                # Skip unsupported files
                if not self._is_supported_file(item_path):
                    continue
                
                tree_item = QTreeWidgetItem()
                tree_item.setText(0, item_path.name)
                tree_item.setData(0, Qt.ItemDataRole.UserRole, str(item_path))
                
                if item_path.is_dir():
                    tree_item.setText(0, f"📁 {item_path.name}")
                    # Add a placeholder child so the folder shows as expandable
                    placeholder = QTreeWidgetItem()
                    placeholder.setText(0, "")
                    tree_item.addChild(placeholder)
                else:
                    tree_item.setText(0, f"📄 {item_path.name}")
                
                if parent_item is None:
                    self.tree.addTopLevelItem(tree_item)
                else:
                    parent_item.addChild(tree_item)
        except PermissionError:
            pass
    
    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle folder expansion to load its contents."""
        path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not path_str:
            return
        
        path = Path(path_str)
        if not path.is_dir():
            return
        
        # Remove placeholder and load actual contents
        if item.childCount() == 1 and item.child(0).text(0) == "":
            item.removeChild(item.child(0))
            self._populate_tree(item, path)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on item."""
        path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not path_str:
            return
        
        path = Path(path_str)
        if path.is_file():
            self.file_selected.emit(str(path))
