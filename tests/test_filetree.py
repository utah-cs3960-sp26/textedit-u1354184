"""Rigorous tests for the FileTreeWidget and its integration."""

import pytest
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from src.file_tree import FileTreeWidget
from src.editor import TextEditor
from src.find_replace import FindReplaceWidget
from src.split_container import SplitContainer


@pytest.fixture(scope="session")
def app():
    """Create a QApplication instance for the test session."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create test files with various extensions
        (tmppath / "script.py").write_text("print('Hello')")
        (tmppath / "style.css").write_text("body { color: blue; }")
        (tmppath / "config.json").write_text('{"key": "value"}')
        (tmppath / "readme.md").write_text("# Test README")
        (tmppath / "data.csv").write_text("name,age\nAlice,30")
        (tmppath / "notes.txt").write_text("Test notes")
        (tmppath / "query.sql").write_text("SELECT * FROM users;")
        
        # Create subdirectory with files
        subdir = tmppath / "subdir"
        subdir.mkdir()
        (subdir / "module.py").write_text("def foo(): pass")
        (subdir / "style.scss").write_text("$color: blue;")
        
        # Create unsupported files that should be filtered
        (tmppath / "image.png").write_text("fake image data")
        (tmppath / "archive.zip").write_text("fake zip data")
        (tmppath / ".hidden").write_text("should not appear")
        
        yield tmppath


@pytest.fixture
def file_tree(app, temp_dir):
    """Create a FileTreeWidget instance."""
    widget = FileTreeWidget()
    widget.load_directory(temp_dir)
    yield widget
    widget.deleteLater()


@pytest.fixture
def split_container(app):
    """Create a SplitContainer instance."""
    container = SplitContainer()
    yield container
    container.deleteLater()


@pytest.fixture
def find_replace(app):
    """Create a FindReplaceWidget instance."""
    widget = FindReplaceWidget()
    yield widget
    widget.deleteLater()


class TestFileTreeBasics:
    """Test basic file tree functionality."""
    
    def test_filetree_loads_directory(self, file_tree, temp_dir):
        """Test that file tree loads a directory."""
        assert file_tree.current_root == temp_dir
        assert file_tree.tree.topLevelItemCount() > 0
    
    def test_filetree_shows_supported_files(self, file_tree):
        """Test that only supported files are shown."""
        items = self._get_all_items(file_tree.tree)
        item_names = [item.text(0) for item in items]
        
        # Check for supported files
        assert any("script.py" in name for name in item_names)
        assert any("style.css" in name for name in item_names)
        assert any("config.json" in name for name in item_names)
        assert any("readme.md" in name for name in item_names)
    
    def test_filetree_filters_unsupported_files(self, file_tree):
        """Test that unsupported files are hidden."""
        items = self._get_all_items(file_tree.tree)
        item_names = [item.text(0) for item in items]
        
        # Check that unsupported files are not shown
        assert not any("image.png" in name for name in item_names)
        assert not any("archive.zip" in name for name in item_names)
    
    def test_filetree_filters_hidden_files(self, file_tree):
        """Test that hidden files (starting with .) are filtered."""
        items = self._get_all_items(file_tree.tree)
        item_names = [item.text(0) for item in items]
        
        assert not any(".hidden" in name for name in item_names)
    
    def test_filetree_shows_folders(self, file_tree):
        """Test that folders are shown."""
        items = self._get_all_items(file_tree.tree)
        item_names = [item.text(0) for item in items]
        
        # Should have a folder icon
        assert any("📁" in name and "subdir" in name for name in item_names)
    
    def test_filetree_shows_file_icons(self, file_tree):
        """Test that file icons are displayed."""
        items = self._get_all_items(file_tree.tree)
        
        # All non-empty leaf items should have file icons
        for item in items:
            if item.childCount() == 0 and item.text(0):  # Leaf node with text
                assert "📄" in item.text(0) or "📁" in item.text(0)
    
    def test_supported_extensions_set(self):
        """Test that supported extensions are properly defined."""
        assert ".py" in FileTreeWidget.SUPPORTED_EXTENSIONS
        assert ".js" in FileTreeWidget.SUPPORTED_EXTENSIONS
        assert ".json" in FileTreeWidget.SUPPORTED_EXTENSIONS
        assert ".md" in FileTreeWidget.SUPPORTED_EXTENSIONS
        assert ".txt" in FileTreeWidget.SUPPORTED_EXTENSIONS
        assert ".html" in FileTreeWidget.SUPPORTED_EXTENSIONS
    
    def test_is_supported_file(self, file_tree, temp_dir):
        """Test file extension checking."""
        assert file_tree._is_supported_file(temp_dir / "script.py")
        assert file_tree._is_supported_file(temp_dir / "style.css")
        assert not file_tree._is_supported_file(temp_dir / "image.png")
        assert file_tree._is_supported_file(temp_dir)  # Directories always supported
    
    @staticmethod
    def _get_all_items(tree):
        """Helper to get all items in a tree widget."""
        items = []
        for i in range(tree.topLevelItemCount()):
            items.append(tree.topLevelItem(i))
            items.extend(TestFileTreeBasics._get_child_items(tree.topLevelItem(i)))
        return items
    
    @staticmethod
    def _get_child_items(parent):
        """Helper to recursively get child items."""
        items = []
        for i in range(parent.childCount()):
            child = parent.child(i)
            items.append(child)
            items.extend(TestFileTreeBasics._get_child_items(child))
        return items


class TestFileTreeFileOpening:
    """Test opening files through the file tree."""
    
    def test_file_selected_signal_emitted(self, file_tree, temp_dir):
        """Test that file_selected signal is emitted when file is double-clicked."""
        signal_data = []
        file_tree.file_selected.connect(lambda path: signal_data.append(path))
        
        # Find and click a file item
        items = self._get_all_leaf_items(file_tree.tree)
        py_file = next((item for item in items if "script.py" in item.text(0)), None)
        
        if py_file:
            file_tree._on_item_double_clicked(py_file, 0)
            assert len(signal_data) > 0
            assert "script.py" in signal_data[0]
    
    def test_opening_python_file(self, split_container, file_tree, temp_dir):
        """Test opening a Python file."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        py_file = temp_dir / "script.py"
        file_tree.file_selected.emit(str(py_file))
        
        editor = split_container.current_editor()
        assert editor is not None
        assert "Hello" in editor.toPlainText()
    
    def test_opening_json_file(self, split_container, file_tree, temp_dir):
        """Test opening a JSON file."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        json_file = temp_dir / "config.json"
        file_tree.file_selected.emit(str(json_file))
        
        editor = split_container.current_editor()
        assert editor is not None
        assert "key" in editor.toPlainText()
    
    def test_opening_markdown_file(self, split_container, file_tree, temp_dir):
        """Test opening a Markdown file."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        md_file = temp_dir / "readme.md"
        file_tree.file_selected.emit(str(md_file))
        
        editor = split_container.current_editor()
        assert editor is not None
        assert "README" in editor.toPlainText()
    
    def test_opening_text_file(self, split_container, file_tree, temp_dir):
        """Test opening a plain text file."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        txt_file = temp_dir / "notes.txt"
        file_tree.file_selected.emit(str(txt_file))
        
        editor = split_container.current_editor()
        assert editor is not None
        assert "notes" in editor.toPlainText()
    
    def test_opening_multiple_files_creates_tabs(self, split_container, file_tree, temp_dir):
        """Test that opening multiple files creates multiple tabs."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        file_tree.file_selected.emit(str(temp_dir / "script.py"))
        file_tree.file_selected.emit(str(temp_dir / "config.json"))
        
        active_tabs = split_container.active_tab_widget()
        assert active_tabs.count() >= 2
    
    def test_opening_already_open_file_switches_tab(self, split_container, file_tree, temp_dir):
        """Test that opening an already-open file switches to that tab."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        py_file = str(temp_dir / "script.py")
        file_tree.file_selected.emit(py_file)
        first_index = split_container.active_tab_widget().currentIndex()
        
        file_tree.file_selected.emit(str(temp_dir / "config.json"))
        
        file_tree.file_selected.emit(py_file)
        second_index = split_container.active_tab_widget().currentIndex()
        
        # Opening the same file again should switch to it
        assert first_index == second_index
    
    @staticmethod
    def _get_all_leaf_items(tree):
        """Get all leaf items in tree."""
        items = []
        for i in range(tree.topLevelItemCount()):
            items.extend(TestFileTreeFileOpening._get_leaf_items(tree.topLevelItem(i)))
        return items
    
    @staticmethod
    def _get_leaf_items(item):
        """Recursively get leaf items."""
        if item.childCount() == 0:
            return [item]
        items = []
        for i in range(item.childCount()):
            items.extend(TestFileTreeFileOpening._get_leaf_items(item.child(i)))
        return items


class TestFileTreeWithEditing:
    """Test editing files opened from the file tree."""
    
    def test_editing_file_opened_from_tree(self, split_container, file_tree, temp_dir):
        """Test that files opened from tree can be edited."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        file_tree.file_selected.emit(str(temp_dir / "notes.txt"))
        editor = split_container.current_editor()
        
        original_text = editor.toPlainText()
        # Use editor's methods to edit like a user would
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        editor.insertPlainText("\nAdded line")
        
        assert "Added line" in editor.toPlainText()
    
    def test_undo_redo_in_tree_opened_file(self, split_container, file_tree, temp_dir):
        """Test undo/redo works on files opened from tree."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        file_tree.file_selected.emit(str(temp_dir / "notes.txt"))
        editor = split_container.current_editor()
        
        # Use insertPlainText like a user would
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        editor.insertPlainText("\nNew text")
        
        assert "New text" in editor.toPlainText()
        
        editor.undo()
        assert "New text" not in editor.toPlainText()
        
        editor.redo()
        assert "New text" in editor.toPlainText()


class TestFileTreeWithSplitViews:
    """Test file tree integration with split views."""
    
    def test_open_file_in_split_pane(self, split_container, file_tree, temp_dir):
        """Test opening files in different split panes."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        # Open first file
        file_tree.file_selected.emit(str(temp_dir / "script.py"))
        
        # Create a split
        split_container.split_horizontal()
        
        # Open different file in the new split
        file_tree.file_selected.emit(str(temp_dir / "config.json"))
        
        # Both panes should have files
        all_tabs = split_container._get_all_tab_widgets()
        assert len(all_tabs) >= 2
    
    def test_find_in_split_pane_with_tree_opened_file(self, split_container, file_tree, find_replace, temp_dir):
        """Test find/replace works on files opened from tree in split panes."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        # Open file with searchable content
        (temp_dir / "searchable.txt").write_text("apple\norange\napple")
        file_tree.file_selected.emit(str(temp_dir / "searchable.txt"))
        
        editor = split_container.current_editor()
        find_replace.set_editor(editor)
        find_replace.find_input.setText("apple")
        
        # Find should work
        assert find_replace.find_next()
        assert editor.textCursor().selectedText() == "apple"


class TestFileTreeWithFindReplace:
    """Test file tree integration with find and replace."""
    
    def test_find_in_tree_opened_file(self, split_container, file_tree, find_replace, temp_dir):
        """Test finding text in file opened from tree."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        file_tree.file_selected.emit(str(temp_dir / "script.py"))
        editor = split_container.current_editor()
        find_replace.set_editor(editor)
        
        find_replace.find_input.setText("Hello")
        assert find_replace.find_next()
    
    def test_replace_in_tree_opened_file(self, split_container, file_tree, find_replace, temp_dir):
        """Test replacing text in file opened from tree."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        (temp_dir / "replaceable.txt").write_text("foo bar foo")
        file_tree.file_selected.emit(str(temp_dir / "replaceable.txt"))
        
        editor = split_container.current_editor()
        find_replace.set_editor(editor)
        find_replace.find_input.setText("foo")
        find_replace.replace_input.setText("baz")
        
        count = find_replace.replace_all()
        assert count == 2
        assert "foo" not in editor.toPlainText()
        assert "baz" in editor.toPlainText()
    
    def test_find_case_sensitive_in_tree_opened_file(self, split_container, file_tree, find_replace, temp_dir):
        """Test case-sensitive find in tree-opened file."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        (temp_dir / "case.txt").write_text("Hello\nhello\nHELLO")
        file_tree.file_selected.emit(str(temp_dir / "case.txt"))
        
        editor = split_container.current_editor()
        find_replace.set_editor(editor)
        find_replace.find_input.setText("hello")
        find_replace.case_sensitive_cb.setChecked(True)
        
        assert find_replace.find_next()
        assert editor.textCursor().selectedText() == "hello"


class TestFileTreeAdvanced:
    """Test advanced file tree scenarios."""
    
    def test_folder_expansion(self, file_tree, temp_dir):
        """Test that folders can be expanded to show contents."""
        # Find the subdir folder
        items = self._get_all_items(file_tree.tree)
        subdir_item = next((item for item in items if "subdir" in item.text(0)), None)
        
        if subdir_item:
            # Should have expandable placeholder initially
            assert subdir_item.childCount() > 0
            
            # Simulate expansion
            file_tree._on_item_expanded(subdir_item)
            
            # Should now have actual files
            assert subdir_item.childCount() > 0
            item_names = [subdir_item.child(i).text(0) for i in range(subdir_item.childCount())]
            assert any("module.py" in name for name in item_names)
    
    def test_multiple_file_types_in_same_folder(self, file_tree, temp_dir):
        """Test that multiple file types are shown together."""
        items = self._get_all_items(file_tree.tree)
        item_names = [item.text(0) for item in items]
        
        # Should have mixed file types
        assert any(".py" in name for name in item_names)
        assert any(".json" in name for name in item_names)
        assert any(".md" in name for name in item_names)
    
    def test_open_sql_file(self, split_container, file_tree, temp_dir):
        """Test opening SQL files."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        file_tree.file_selected.emit(str(temp_dir / "query.sql"))
        editor = split_container.current_editor()
        
        assert editor is not None
        assert "SELECT" in editor.toPlainText()
    
    def test_open_csv_file(self, split_container, file_tree, temp_dir):
        """Test opening CSV files."""
        file_tree.file_selected.connect(split_container.open_file_path)
        
        file_tree.file_selected.emit(str(temp_dir / "data.csv"))
        editor = split_container.current_editor()
        
        assert editor is not None
        assert "Alice" in editor.toPlainText()
    
    @staticmethod
    def _get_all_items(tree):
        """Helper to get all items in a tree widget."""
        items = []
        for i in range(tree.topLevelItemCount()):
            items.append(tree.topLevelItem(i))
            items.extend(TestFileTreeAdvanced._get_child_items(tree.topLevelItem(i)))
        return items
    
    @staticmethod
    def _get_child_items(parent):
        """Helper to recursively get child items."""
        items = []
        for i in range(parent.childCount()):
            child = parent.child(i)
            items.append(child)
            items.extend(TestFileTreeAdvanced._get_child_items(child))
        return items
