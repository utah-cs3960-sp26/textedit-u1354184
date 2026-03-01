"""Tests for TextEditor large-file mode and GUI-action interactions."""

import os
import pytest
import tempfile

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt

from src.editor import TextEditor
from src.large_file_backend import LARGE_FILE_THRESHOLD


@pytest.fixture(scope="session")
def app():
    """Create a QApplication instance for the test session."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def editor(app):
    """Create a TextEditor instance."""
    ed = TextEditor()
    yield ed
    ed.deleteLater()


@pytest.fixture
def large_file(tmp_path):
    """Create a file large enough to trigger large-file mode (>10MB)."""
    path = tmp_path / "large_test.txt"
    # Write enough data to exceed 10MB threshold
    with open(str(path), 'w') as f:
        for i in range(120_000):
            f.write(f"Line {i:06d}: " + "x" * 80 + "\n")
    assert os.path.getsize(str(path)) >= LARGE_FILE_THRESHOLD
    return str(path)


@pytest.fixture
def small_large_file(tmp_path):
    """Create a moderately large file for testing (just above threshold)."""
    path = tmp_path / "medium.txt"
    line_template = "Line {:06d}: content here for searching and testing purposes\n"
    num_lines = (LARGE_FILE_THRESHOLD // len(line_template.format(0))) + 10
    with open(str(path), 'w') as f:
        for i in range(num_lines):
            f.write(line_template.format(i))
    return str(path)


class TestEditorLargeFileMode:
    """Test editor behavior in large-file mode."""

    def test_load_large_file(self, editor, large_file):
        """Test loading a large file activates large-file mode."""
        result = editor.load_file(large_file)
        assert result is True
        assert editor.is_large_file_mode()
        assert editor.file_path == large_file

    def test_total_line_count_large_file(self, editor, large_file):
        """Test total_line_count reflects full file, not just visible window."""
        editor.load_file(large_file)
        total = editor.total_line_count
        # Should report full file line count, not just what's in the widget
        assert total > 10000

    def test_total_line_count_small_file(self, editor):
        """Test total_line_count for small (normal mode) files."""
        editor.setPlainText("Line 1\nLine 2\nLine 3")
        assert editor.total_line_count == 3

    def test_cursor_position_with_offset(self, editor, large_file):
        """Test cursor position signal includes window offset."""
        editor.load_file(large_file)
        received = []
        editor.cursor_position_changed.connect(lambda l, c: received.append((l, c)))

        # Move cursor to trigger signal (must change position)
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Down)
        editor.setTextCursor(cursor)

        assert len(received) > 0

    def test_save_large_file(self, editor, large_file, tmp_path):
        """Test saving a large file."""
        editor.load_file(large_file)
        save_path = str(tmp_path / "saved_large.txt")
        result = editor.save_file(save_path)
        assert result is True
        assert os.path.exists(save_path)

    def test_save_large_file_default_path(self, editor, large_file):
        """Test saving large file to original path."""
        editor.load_file(large_file)
        result = editor.save_file()
        assert result is True

    def test_save_large_file_error(self, editor, large_file):
        """Test save_large_file with invalid path."""
        editor.load_file(large_file)
        result = editor.save_file("/nonexistent/dir/file.txt")
        assert result is False

    def test_count_matches_in_file(self, editor, large_file):
        """Test counting matches across full large file."""
        editor.load_file(large_file)
        count = editor.count_matches_in_file("Line", True, False)
        assert count > 0

    def test_count_matches_no_backend(self, editor):
        """Test count_matches returns 0 when not in large file mode."""
        editor.setPlainText("Hello")
        count = editor.count_matches_in_file("Hello", True, False)
        assert count == 0

    def test_find_next_in_file(self, editor, small_large_file):
        """Test finding next match in large file."""
        editor.load_file(small_large_file)
        result = editor.find_next_in_file("content", True, False)
        assert result is True

    def test_find_next_no_backend(self, editor):
        """Test find_next_in_file returns False without backend."""
        editor.setPlainText("Hello")
        assert editor.find_next_in_file("Hello", True, False) is False

    def test_find_prev_in_file(self, editor, small_large_file):
        """Test finding previous match in large file."""
        editor.load_file(small_large_file)
        # Move cursor to end-ish
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        result = editor.find_prev_in_file("content", True, False)
        assert result is True

    def test_find_prev_no_backend(self, editor):
        """Test find_prev_in_file returns False without backend."""
        editor.setPlainText("Hello")
        assert editor.find_prev_in_file("Hello", True, False) is False

    def test_replace_all_in_file(self, editor, small_large_file):
        """Test replacing all in large file."""
        editor.load_file(small_large_file)
        count = editor.replace_all_in_file("content", "REPLACED", True, False)
        assert count > 0

    def test_replace_all_no_backend(self, editor):
        """Test replace_all_in_file returns 0 without backend."""
        editor.setPlainText("Hello")
        assert editor.replace_all_in_file("Hello", "Hi", True, False) == 0

    def test_go_to_line_large_file(self, editor, small_large_file):
        """Test go_to_line in large file mode reloads window."""
        editor.load_file(small_large_file)
        editor.go_to_line(100)
        # Should not crash; cursor should be repositioned

    def test_is_large_file_mode_false_for_normal(self, editor):
        """Test is_large_file_mode returns False for normal files."""
        editor.setPlainText("Normal text")
        assert not editor.is_large_file_mode()

    def test_load_large_file_error(self, editor, tmp_path):
        """Test loading a nonexistent file as large file returns False."""
        result = editor.load_file("/nonexistent/large/file.txt")
        assert result is False

    def test_load_replaces_existing_backend(self, editor, small_large_file, tmp_path):
        """Test that loading a second large file replaces the first backend."""
        editor.load_file(small_large_file)
        assert editor.is_large_file_mode()

        # Create another large file
        path2 = tmp_path / "large2.txt"
        line = "Second file line {:06d}\n"
        num_lines = (LARGE_FILE_THRESHOLD // len(line.format(0))) + 10
        with open(str(path2), 'w') as f:
            for i in range(num_lines):
                f.write(line.format(i))

        editor.load_file(str(path2))
        assert editor.is_large_file_mode()
        assert editor.file_path == str(path2)


class TestEditorGUIActions:
    """Test editor operations that simulate real GUI interactions."""

    def test_type_text_via_cursor(self, editor):
        """Test typing text by inserting via cursor (simulates keystrokes)."""
        editor.setPlainText("")
        cursor = editor.textCursor()
        cursor.insertText("Hello, World!")
        assert editor.toPlainText() == "Hello, World!"
        assert editor.is_modified

    def test_select_and_delete(self, editor):
        """Test selecting text and deleting it."""
        editor.setPlainText("Hello World")
        cursor = editor.textCursor()
        cursor.setPosition(5)
        cursor.setPosition(11, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        cursor.removeSelectedText()
        assert editor.toPlainText() == "Hello"

    def test_undo_redo_cycle(self, editor):
        """Test undo/redo works properly through multiple operations."""
        editor.setPlainText("")
        editor.document().setModified(False)
        editor.document().clearUndoRedoStacks()

        # Use separate edit blocks to create undoable steps
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        cursor.insertText("Step 1")
        cursor.endEditBlock()
        assert editor.toPlainText() == "Step 1"

        cursor.beginEditBlock()
        cursor.insertText(" Step 2")
        cursor.endEditBlock()
        assert editor.toPlainText() == "Step 1 Step 2"

        editor.undo()
        assert editor.toPlainText() == "Step 1"

        editor.redo()
        assert editor.toPlainText() == "Step 1 Step 2"

    def test_cut_paste_cycle(self, editor):
        """Test cutting and pasting text."""
        editor.setPlainText("ABCDEF")
        # Select "CD"
        cursor = editor.textCursor()
        cursor.setPosition(2)
        cursor.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)

        editor.cut()
        assert editor.toPlainText() == "ABEF"

        # Move to end and paste
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        editor.paste()
        assert editor.toPlainText() == "ABEFCD"

    def test_multiline_editing(self, editor):
        """Test editing across multiple lines."""
        editor.setPlainText("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")

        # Delete line 3
        cursor = editor.textCursor()
        cursor.setPosition(14)  # On line 3
        editor.setTextCursor(cursor)
        editor.delete_line()

        # Move line 2 down
        cursor = editor.textCursor()
        cursor.setPosition(7)  # On line 2
        editor.setTextCursor(cursor)
        editor.move_line_down()

        text = editor.toPlainText()
        lines = text.split('\n')
        assert len(lines) == 4
        # Line 1 should still be first
        assert lines[0] == "Line 1"

    def test_select_word_in_middle(self, editor):
        """Test selecting a word in the middle of a line."""
        editor.setPlainText("The quick brown fox")
        cursor = editor.textCursor()
        cursor.setPosition(6)  # In "quick"
        editor.setTextCursor(cursor)

        editor.select_word()
        assert editor.textCursor().selectedText() == "quick"

    def test_go_to_line_and_verify(self, editor):
        """Test go_to_line positions cursor correctly."""
        editor.setPlainText("A\nB\nC\nD\nE")
        editor.go_to_line(3)
        cursor = editor.textCursor()
        assert cursor.blockNumber() == 2  # 0-indexed

    def test_duplicate_then_undo(self, editor):
        """Test duplicating a line and then undoing."""
        editor.setPlainText("Original")
        editor.document().setModified(False)
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)

        editor.duplicate_line()
        lines = editor.toPlainText().split('\n')
        assert len(lines) == 2
        assert lines[0] == lines[1] == "Original"

        editor.undo()
        assert editor.toPlainText() == "Original"

    def test_rapid_text_insertion(self, editor):
        """Test rapid text insertion (simulates fast typing)."""
        editor.setPlainText("")
        cursor = editor.textCursor()
        for char in "Hello World!":
            cursor.insertText(char)
        assert editor.toPlainText() == "Hello World!"

    def test_modification_flag_resets_on_save(self, editor, tmp_path):
        """Test that saving resets the modification flag."""
        test_file = tmp_path / "mod_test.txt"
        editor.setPlainText("Content")
        editor.save_file(str(test_file))
        assert not editor.is_modified

        cursor = editor.textCursor()
        cursor.insertText("More")
        assert editor.is_modified

        editor.save_file()
        assert not editor.is_modified
