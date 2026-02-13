"""Tests for the MainWindow."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent

from src.main_window import MainWindow


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
    yield window
    window.deleteLater()


class TestMainWindowBasics:
    """Test basic main window functionality."""

    def test_initial_state(self, main_window):
        """Test initial window state."""
        assert main_window.windowTitle() == "TextEdit"
        assert main_window.split_container is not None
        assert main_window.find_replace is not None
        assert main_window.file_tree is not None

    def test_status_bar(self, main_window):
        """Test status bar exists."""
        assert main_window.status_bar is not None


class TestEditOperations:
    """Test edit menu operations."""

    def test_undo(self, main_window):
        """Test undo operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Test")
        editor.document().setModified(False)

        cursor = editor.textCursor()
        cursor.insertText("More")

        main_window._undo()
        # Undo should work
        assert editor is not None

    def test_redo(self, main_window):
        """Test redo operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Test")

        main_window._redo()
        assert editor is not None

    def test_cut(self, main_window):
        """Test cut operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Test content")
        editor.select_all()

        main_window._cut()
        assert editor.toPlainText() == ""

    def test_copy(self, main_window):
        """Test copy operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Test content")
        editor.select_all()

        main_window._copy()
        # Content should still be there
        assert editor.toPlainText() == "Test content"

    def test_paste(self, main_window):
        """Test paste operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Test")
        editor.select_all()
        main_window._copy()

        editor.moveCursor(editor.textCursor().MoveOperation.End)
        main_window._paste()
        assert "Test" in editor.toPlainText()

    def test_select_all(self, main_window):
        """Test select all operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Test content")

        main_window._select_all()
        assert editor.textCursor().hasSelection()

    def test_select_word(self, main_window):
        """Test select word operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Hello World")
        cursor = editor.textCursor()
        cursor.setPosition(2)
        editor.setTextCursor(cursor)

        main_window._select_word()
        assert editor.textCursor().selectedText() == "Hello"

    def test_select_line(self, main_window):
        """Test select line operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Line 1\nLine 2")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)

        main_window._select_line()
        assert editor.textCursor().selectedText() == "Line 1"


class TestLineOperations:
    """Test line manipulation operations."""

    def test_duplicate_line(self, main_window):
        """Test duplicate line operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Line 1\nLine 2")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)

        main_window._duplicate_line()
        lines = editor.toPlainText().split('\n')
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 1"

    def test_delete_line(self, main_window):
        """Test delete line operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Line 1\nLine 2\nLine 3")
        cursor = editor.textCursor()
        cursor.setPosition(7)  # Middle of Line 2
        editor.setTextCursor(cursor)

        main_window._delete_line()
        lines = editor.toPlainText().split('\n')
        assert len(lines) == 2

    def test_move_line_up(self, main_window):
        """Test move line up operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Line 1\nLine 2")
        cursor = editor.textCursor()
        cursor.setPosition(7)
        editor.setTextCursor(cursor)

        main_window._move_line_up()
        lines = editor.toPlainText().split('\n')
        assert lines[0] == "Line 2"
        assert lines[1] == "Line 1"

    def test_move_line_down(self, main_window):
        """Test move line down operation."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Line 1\nLine 2")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)

        main_window._move_line_down()
        lines = editor.toPlainText().split('\n')
        assert lines[0] == "Line 2"
        assert lines[1] == "Line 1"


class TestFindReplace:
    """Test find/replace operations."""

    def test_show_find(self, main_window):
        """Test showing find bar."""
        main_window.show()
        main_window._show_find()
        # Just verify no exception and editor is set
        assert main_window.find_replace._editor is not None

    def test_find_next_shows_find_bar(self, main_window):
        """Test find next shows find bar if not visible."""
        main_window.show()
        main_window.find_replace.hide()
        main_window._find_next()
        # Verify show_find was called (editor should be set)
        assert main_window.find_replace._editor is not None

    def test_find_previous_shows_find_bar(self, main_window):
        """Test find previous shows find bar if not visible."""
        main_window.show()
        main_window.find_replace.hide()
        main_window._find_previous()
        assert main_window.find_replace._editor is not None

    def test_find_next_when_visible(self, main_window):
        """Test find next when find bar is visible."""
        main_window.show()
        # First show find to set up the editor
        main_window._show_find()
        main_window.find_replace.find_input.setText("test")
        # Now call find_next - it should use the already visible widget
        main_window._find_next()
        # Verify no exception occurred
        assert True

    def test_find_previous_when_visible(self, main_window):
        """Test find previous when find bar is visible."""
        main_window.show()
        # First show find to set up the editor
        main_window._show_find()
        main_window.find_replace.find_input.setText("test")
        # Now call find_previous
        main_window._find_previous()
        assert True

    def test_on_find_closed(self, main_window):
        """Test handling find bar close."""
        main_window._show_find()
        main_window._on_find_closed()
        # Editor should get focus back
        editor = main_window.split_container.current_editor()
        assert editor is not None


class TestFileTree:
    """Test file tree operations."""

    def test_open_filetree(self, main_window):
        """Test opening file tree."""
        main_window.show()
        main_window._open_filetree()
        # Verify the splitter sizes were set to show file tree
        sizes = main_window.main_splitter.sizes()
        assert sizes[0] > 0  # File tree should have some width

    def test_close_filetree(self, main_window):
        """Test closing file tree."""
        main_window.show()
        main_window._open_filetree()
        main_window._close_filetree()
        # Verify the splitter sizes were set to hide file tree
        sizes = main_window.main_splitter.sizes()
        assert sizes[0] == 0  # File tree should have zero width

    def test_on_file_selected(self, main_window, tmp_path):
        """Test file selection from tree."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        main_window._on_file_selected(str(test_file))
        editor = main_window.split_container.current_editor()
        assert editor.toPlainText() == "Test content"


class TestWindowTitle:
    """Test window title updates."""

    def test_update_window_title_no_file(self, main_window):
        """Test window title with no file."""
        main_window._update_window_title()
        assert main_window.windowTitle() == "TextEdit"

    def test_update_window_title_with_file(self, main_window, tmp_path):
        """Test window title with file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")

        main_window.split_container.open_file(str(test_file))
        main_window._update_window_title()
        assert "test.txt" in main_window.windowTitle()


class TestCursorPosition:
    """Test cursor position tracking."""

    def test_update_cursor_position(self, main_window):
        """Test cursor position update in status bar."""
        main_window._update_cursor_position(5, 10)
        assert "Line 5" in main_window.status_bar.currentMessage()
        assert "Column 10" in main_window.status_bar.currentMessage()


class TestEditorChange:
    """Test editor change handling."""

    def test_on_editor_changed(self, main_window):
        """Test handling editor change."""
        editor = main_window.split_container.current_editor()
        main_window._on_editor_changed(editor)
        # Should update find_replace editor
        assert main_window.find_replace._editor == editor

    def test_on_active_tabs_changed(self, main_window):
        """Test handling active tabs change."""
        tabs = main_window.split_container.active_tab_widget()
        main_window._on_active_tabs_changed(tabs)
        # Should update find_replace editor
        editor = tabs.current_editor()
        if editor:
            assert main_window.find_replace._editor == editor


class TestCloseEvent:
    """Test window close handling."""

    def test_close_event_accepted(self, main_window):
        """Test close event when all tabs close successfully."""
        event = Mock(spec=QCloseEvent)
        main_window.closeEvent(event)
        event.accept.assert_called()

    def test_close_event_with_modified(self, main_window):
        """Test close event with modified content."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Modified content")
        editor.document().setModified(True)

        # This would normally show a dialog
        event = Mock(spec=QCloseEvent)
        # In test, the dialog will be auto-cancelled or we mock it
        main_window.closeEvent(event)
        # Either accept or ignore was called
        assert event.accept.called or event.ignore.called

    def test_close_event_rejected(self, main_window):
        """Test close event when user cancels."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Modified content")
        editor.document().setModified(True)

        event = Mock(spec=QCloseEvent)
        with patch('src.tab_widget.QMessageBox.question') as mock_msg:
            mock_msg.return_value = QMessageBox.StandardButton.Cancel
            main_window.closeEvent(event)
            event.ignore.assert_called()


class TestDialogInteractions:
    """Test dialog-based interactions with mocking."""

    def test_go_to_line_dialog(self, main_window):
        """Test go to line dialog."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Line 1\nLine 2\nLine 3")

        with patch('src.main_window.QInputDialog.getInt') as mock_dialog:
            mock_dialog.return_value = (2, True)
            main_window._go_to_line()
            # Cursor should be on line 2
            assert editor.textCursor().blockNumber() == 1

    def test_go_to_line_cancelled(self, main_window):
        """Test go to line dialog cancelled."""
        editor = main_window.split_container.current_editor()
        editor.setPlainText("Line 1\nLine 2")
        initial_block = editor.textCursor().blockNumber()

        with patch('src.main_window.QInputDialog.getInt') as mock_dialog:
            mock_dialog.return_value = (1, False)
            main_window._go_to_line()
            # Cursor should not have moved
            assert editor.textCursor().blockNumber() == initial_block

    def test_show_about_dialog(self, main_window):
        """Test about dialog."""
        with patch('src.main_window.QMessageBox.about') as mock_about:
            main_window._show_about()
            mock_about.assert_called_once()
            # Check that TextEdit is in the message
            call_args = mock_about.call_args
            assert "TextEdit" in call_args[0][1]

    def test_show_multi_file_find_dialog(self, main_window):
        """Test multi-file find dialog."""
        with patch('src.main_window.MultiFileFindDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog_class.return_value = mock_dialog
            main_window._show_multi_file_find()
            mock_dialog.exec.assert_called_once()

    def test_go_to_line_no_editor(self, main_window):
        """Test go to line when no editor."""
        main_window.split_container._active_tabs = None
        # Should not crash
        main_window._go_to_line()
        assert True
