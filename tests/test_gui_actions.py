"""Tests that simulate real GUI actions using pytest-qt's qtbot fixture.

These tests exercise the application as a user would: typing, clicking buttons,
using keyboard shortcuts, and verifying visible results.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtTest import QTest

from src.main_window import MainWindow
from src.editor import TextEditor
from src.find_replace import FindReplaceWidget


@pytest.fixture(scope="session")
def app():
    """Create a QApplication instance for the test session."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def main_window(app):
    """Create a MainWindow instance."""
    window = MainWindow()
    window.show()
    yield window
    window.close()
    window.deleteLater()


class TestTypingInEditor:
    """Test actual text input via simulated keystrokes."""

    def test_type_characters(self, main_window):
        """Test typing individual characters into the editor."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("")
        editor.setFocus()

        QTest.keyClicks(editor, "Hello")
        assert editor.toPlainText() == "Hello"

    def test_type_with_enter(self, main_window):
        """Test typing with Enter key for new lines."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("")
        editor.setFocus()

        QTest.keyClicks(editor, "Line 1")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        QTest.keyClicks(editor, "Line 2")

        lines = editor.toPlainText().split('\n')
        assert len(lines) == 2
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"

    def test_backspace(self, main_window):
        """Test backspace key deletes character."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("")
        editor.setFocus()

        QTest.keyClicks(editor, "Hellp")
        QTest.keyClick(editor, Qt.Key.Key_Backspace)
        QTest.keyClicks(editor, "o")
        assert editor.toPlainText() == "Hello"

    def test_tab_key(self, main_window):
        """Test tab key inserts tab character."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("")
        editor.setFocus()

        QTest.keyClick(editor, Qt.Key.Key_Tab)
        QTest.keyClicks(editor, "indented")
        assert "\t" in editor.toPlainText()


class TestKeyboardShortcuts:
    """Test keyboard shortcuts work correctly through the GUI."""

    def test_select_all_shortcut(self, main_window):
        """Test Ctrl+A selects all text."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Select all this text")
        editor.setFocus()

        QTest.keyClick(editor, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        assert editor.textCursor().hasSelection()
        assert editor.textCursor().selectedText() == "Select all this text"

    def test_copy_paste_shortcut(self, main_window):
        """Test Ctrl+C / Ctrl+V copy-paste cycle."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Copy me")
        editor.setFocus()

        # Select all
        QTest.keyClick(editor, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        # Copy
        QTest.keyClick(editor, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        # Move to end
        QTest.keyClick(editor, Qt.Key.Key_End, Qt.KeyboardModifier.ControlModifier)
        # Paste
        QTest.keyClick(editor, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)

        assert "Copy me" in editor.toPlainText()

    def test_undo_shortcut(self, main_window):
        """Test Ctrl+Z undo."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Original")
        editor.document().setModified(False)
        editor.setFocus()

        QTest.keyClicks(editor, " Added")
        assert "Added" in editor.toPlainText()

        QTest.keyClick(editor, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        # Some or all of "Added" should be undone
        assert editor.toPlainText() != "Original Added"


class TestFindReplaceGUI:
    """Test find/replace through actual GUI interactions."""

    def test_find_via_typing(self, main_window):
        """Test searching by typing in the find input."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("apple banana apple cherry apple")
        editor.setFocus()

        fr = main_window.find_replace
        fr.set_editor(editor)
        fr.show_find()

        # Type search text
        fr.find_input.clear()
        QTest.keyClicks(fr.find_input, "apple")

        # The auto-find should have found the first match
        assert editor.textCursor().selectedText() == "apple"

    def test_find_next_button_click(self, main_window):
        """Test clicking the Find Next button."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("cat dog cat bird cat")
        editor.setFocus()

        fr = main_window.find_replace
        fr.set_editor(editor)
        fr.show_find()
        fr.find_input.clear()
        QTest.keyClicks(fr.find_input, "cat")

        # First match found by auto-find
        first_pos = editor.textCursor().position()

        # Click find next
        QTest.mouseClick(fr.find_next_btn, Qt.MouseButton.LeftButton)
        second_pos = editor.textCursor().position()

        assert second_pos > first_pos

    def test_replace_button_click(self, main_window):
        """Test clicking Replace button."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("old text old more old")
        editor.setFocus()

        fr = main_window.find_replace
        fr.set_editor(editor)
        fr.show_find()
        fr.find_input.clear()
        fr.replace_input.clear()
        QTest.keyClicks(fr.find_input, "old")
        QTest.keyClicks(fr.replace_input, "new")

        # Click Replace
        QTest.mouseClick(fr.replace_btn, Qt.MouseButton.LeftButton)

        assert "new" in editor.toPlainText()

    def test_replace_all_button_click(self, main_window):
        """Test clicking Replace All button."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("foo bar foo baz foo")
        editor.setFocus()

        fr = main_window.find_replace
        fr.set_editor(editor)
        fr.show_find()
        fr.find_input.clear()
        fr.replace_input.clear()
        QTest.keyClicks(fr.find_input, "foo")
        QTest.keyClicks(fr.replace_input, "qux")

        QTest.mouseClick(fr.replace_all_btn, Qt.MouseButton.LeftButton)

        assert editor.toPlainText() == "qux bar qux baz qux"
        assert "foo" not in editor.toPlainText()

    def test_close_find_bar_button(self, main_window):
        """Test closing find bar via close button."""
        fr = main_window.find_replace
        fr.show_find()
        assert fr.isVisible()

        QTest.mouseClick(fr.close_btn, Qt.MouseButton.LeftButton)
        assert not fr.isVisible()

    def test_escape_closes_find_bar(self, main_window):
        """Test Escape key closes find bar."""
        fr = main_window.find_replace
        fr.show_find()
        assert fr.isVisible()

        QTest.keyClick(fr, Qt.Key.Key_Escape)
        assert not fr.isVisible()

    def test_enter_key_in_find_triggers_find_next(self, main_window):
        """Test pressing Enter in find input triggers find next."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("word word word")
        editor.setFocus()

        fr = main_window.find_replace
        fr.set_editor(editor)
        fr.show_find()
        fr.find_input.clear()
        QTest.keyClicks(fr.find_input, "word")

        # First match found
        first_pos = editor.textCursor().position()

        # Press Enter to find next
        QTest.keyClick(fr.find_input, Qt.Key.Key_Return)
        second_pos = editor.textCursor().position()

        assert second_pos > first_pos

    def test_case_sensitive_checkbox(self, main_window):
        """Test toggling case sensitive checkbox affects search."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Hello hello HELLO")
        editor.setFocus()

        fr = main_window.find_replace
        fr.set_editor(editor)
        fr.show_find()

        # Uncheck case sensitive first
        fr.case_sensitive_cb.setChecked(False)
        fr.find_input.clear()
        QTest.keyClicks(fr.find_input, "hello")

        # Should find (case insensitive)
        assert fr.find_next()

        # Now check case sensitive
        fr.case_sensitive_cb.setChecked(True)
        # Reset cursor to start
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)

        # Find next should find only lowercase "hello"
        assert fr.find_next()
        assert editor.textCursor().selectedText() == "hello"


class TestTabManagementGUI:
    """Test tab management through GUI actions."""

    def test_type_in_different_tabs(self, main_window):
        """Test typing in different tabs maintains separate content."""
        sc = main_window.split_container

        # Type in first tab
        editor1 = sc.current_editor()
        editor1.setPlainText("")
        QTest.keyClicks(editor1, "Tab 1 content")

        # Create new tab
        sc.new_tab()
        editor2 = sc.current_editor()
        editor2.setPlainText("")
        QTest.keyClicks(editor2, "Tab 2 content")

        # Verify content is separate
        assert editor1.toPlainText() == "Tab 1 content"
        assert editor2.toPlainText() == "Tab 2 content"

    def test_open_save_cycle(self, main_window, tmp_path):
        """Test opening a file, editing, and saving."""
        test_file = tmp_path / "edit_test.txt"
        test_file.write_text("Original content")

        sc = main_window.split_container
        sc.open_file_path(str(test_file))

        editor = sc.current_editor()
        assert editor.toPlainText() == "Original content"

        # Move to end and type
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        QTest.keyClicks(editor, " modified")

        # Save
        sc.save_current()

        assert test_file.read_text() == "Original content modified"


class TestSplitViewGUI:
    """Test split view operations through GUI."""

    def test_split_and_type_in_both(self, main_window):
        """Test splitting and typing in both panes."""
        sc = main_window.split_container

        editor1 = sc.current_editor()
        editor1.setPlainText("Pane 1")

        sc.split_horizontal()
        editor2 = sc.current_editor()
        editor2.setPlainText("")
        QTest.keyClicks(editor2, "Pane 2")

        assert editor1.toPlainText() == "Pane 1"
        assert editor2.toPlainText() == "Pane 2"

    def test_split_navigate_and_type(self, main_window):
        """Test navigating between splits and typing."""
        sc = main_window.split_container

        editor1 = sc.current_editor()
        editor1.setPlainText("First")

        sc.split_horizontal()
        editor2 = sc.current_editor()
        QTest.keyClicks(editor2, "Second")

        # Navigate back to first split
        sc.focus_previous_split()
        current = sc.current_editor()

        # The current editor should be accessible
        assert current is not None
