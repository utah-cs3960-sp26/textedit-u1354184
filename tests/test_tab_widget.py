"""Tests for the EditorTabWidget."""

import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from src.tab_widget import EditorTabWidget


@pytest.fixture(scope="session")
def app():
    """Create a QApplication instance for the test session."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def tab_widget(app):
    """Create an EditorTabWidget instance."""
    widget = EditorTabWidget()
    yield widget
    widget.deleteLater()


class TestTabWidgetBasics:
    """Test basic tab widget functionality."""

    def test_initial_state(self, tab_widget):
        """Test initial state has one tab."""
        assert tab_widget.count() == 1
        assert tab_widget.current_editor() is not None

    def test_new_tab(self, tab_widget):
        """Test creating a new tab."""
        initial_count = tab_widget.count()
        editor = tab_widget.new_tab()
        assert editor is not None
        assert tab_widget.count() == initial_count + 1

    def test_new_tab_with_file(self, tab_widget, tmp_path):
        """Test creating a new tab with a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        editor = tab_widget.new_tab(str(test_file))
        assert editor is not None
        assert editor.toPlainText() == "Test content"
        assert tab_widget.tabText(tab_widget.currentIndex()) == "test.txt"

    def test_new_tab_nonexistent_file(self, tab_widget):
        """Test creating a new tab with nonexistent file."""
        initial_count = tab_widget.count()
        editor = tab_widget.new_tab("/nonexistent/file.txt")
        assert editor is None
        assert tab_widget.count() == initial_count  # No new tab created


class TestFileOperations:
    """Test file operations."""

    def test_open_file(self, tab_widget, tmp_path):
        """Test opening a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        editor = tab_widget.open_file(str(test_file))
        assert editor is not None
        assert editor.toPlainText() == "Test content"

    def test_open_file_already_open(self, tab_widget, tmp_path):
        """Test opening a file that's already open switches to it."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        editor1 = tab_widget.open_file(str(test_file))
        tab_widget.new_tab()  # Switch to new tab
        editor2 = tab_widget.open_file(str(test_file))

        assert editor1 is editor2
        assert tab_widget.currentWidget() is editor1

    def test_open_file_reuses_empty_tab(self, tab_widget, tmp_path):
        """Test opening a file reuses empty untitled tab."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        # First tab should be empty untitled
        initial_count = tab_widget.count()
        editor = tab_widget.open_file(str(test_file))

        # Should reuse the empty tab, not create a new one
        assert tab_widget.count() == initial_count

    def test_save_current(self, tab_widget, tmp_path):
        """Test saving current file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Original")

        tab_widget.open_file(str(test_file))
        editor = tab_widget.current_editor()
        editor.setPlainText("Modified")

        result = tab_widget.save_current()
        assert result is True
        assert test_file.read_text() == "Modified"

    def test_save_current_no_editor(self, tab_widget):
        """Test save_current with no current editor."""
        # Remove all tabs
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        result = tab_widget.save_current()
        assert result is False


class TestTabNavigation:
    """Test tab navigation."""

    def test_next_tab(self, tab_widget):
        """Test switching to next tab."""
        tab_widget.new_tab()
        tab_widget.new_tab()
        tab_widget.setCurrentIndex(0)

        tab_widget.next_tab()
        assert tab_widget.currentIndex() == 1

    def test_next_tab_wraps(self, tab_widget):
        """Test next tab wraps around."""
        tab_widget.new_tab()
        tab_widget.setCurrentIndex(tab_widget.count() - 1)

        tab_widget.next_tab()
        assert tab_widget.currentIndex() == 0

    def test_previous_tab(self, tab_widget):
        """Test switching to previous tab."""
        tab_widget.new_tab()
        tab_widget.new_tab()
        tab_widget.setCurrentIndex(2)

        tab_widget.previous_tab()
        assert tab_widget.currentIndex() == 1

    def test_previous_tab_wraps(self, tab_widget):
        """Test previous tab wraps around."""
        tab_widget.new_tab()
        tab_widget.setCurrentIndex(0)

        tab_widget.previous_tab()
        assert tab_widget.currentIndex() == tab_widget.count() - 1

    def test_single_tab_navigation(self, tab_widget):
        """Test navigation with single tab does nothing."""
        # Remove extra tabs to have just one
        while tab_widget.count() > 1:
            tab_widget.removeTab(1)

        tab_widget.next_tab()
        assert tab_widget.currentIndex() == 0

        tab_widget.previous_tab()
        assert tab_widget.currentIndex() == 0


class TestCloseTab:
    """Test tab closing functionality."""

    def test_close_tab(self, tab_widget):
        """Test closing a tab."""
        tab_widget.new_tab()
        initial_count = tab_widget.count()

        result = tab_widget.close_tab(0)
        assert result is True
        assert tab_widget.count() == initial_count - 1

    def test_close_tab_invalid_index(self, tab_widget):
        """Test closing tab with invalid index."""
        result = tab_widget.close_tab(999)
        assert result is False

    def test_close_all_tabs(self, tab_widget):
        """Test closing all tabs."""
        tab_widget.new_tab()
        tab_widget.new_tab()

        result = tab_widget.close_all_tabs()
        assert result is True
        assert tab_widget.count() == 0

    def test_close_last_tab_emits_signal(self, tab_widget):
        """Test closing last tab emits all_tabs_closed signal."""
        received = []
        tab_widget.all_tabs_closed.connect(lambda: received.append(True))

        tab_widget.close_tab(0)
        assert len(received) == 1


class TestTabTitles:
    """Test tab title updates."""

    def test_modified_indicator(self, tab_widget):
        """Test modification indicator in tab title."""
        editor = tab_widget.current_editor()
        editor.setPlainText("Test")
        editor.document().setModified(True)

        tab_widget._update_tab_title(editor)
        title = tab_widget.tabText(tab_widget.currentIndex())
        assert title.startswith("●")

    def test_unmodified_title(self, tab_widget):
        """Test unmodified title has no indicator."""
        editor = tab_widget.current_editor()
        editor.setPlainText("Test")
        editor.document().setModified(False)

        tab_widget._update_tab_title(editor)
        title = tab_widget.tabText(tab_widget.currentIndex())
        assert not title.startswith("●")

    def test_update_title_invalid_index(self, tab_widget):
        """Test updating title for editor not in widget."""
        from src.editor import TextEditor
        orphan_editor = TextEditor()
        # Should not crash
        tab_widget._update_tab_title(orphan_editor)
        orphan_editor.deleteLater()


class TestSignals:
    """Test signal emissions."""

    def test_current_editor_changed(self, tab_widget):
        """Test current_editor_changed signal."""
        received = []
        tab_widget.current_editor_changed.connect(lambda e: received.append(e))

        tab_widget.new_tab()
        assert len(received) > 0


class TestSaveCurrentAs:
    """Test save_current_as functionality."""

    def test_save_current_as_no_editor(self, tab_widget):
        """Test save_current_as with no editor."""
        # Remove all tabs
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        result = tab_widget.save_current_as()
        assert result is False


class TestCloseAllTabs:
    """Test close all tabs."""

    def test_close_all_empty(self, tab_widget):
        """Test close all when no tabs."""
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        result = tab_widget.close_all_tabs()
        assert result is True


class TestOpenFileReuse:
    """Test file opening and tab reuse."""

    def test_open_file_creates_new_when_modified(self, tab_widget, tmp_path):
        """Test that a new tab is created when current tab is modified."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        # Modify the current tab
        editor = tab_widget.current_editor()
        editor.setPlainText("Modified")
        editor.document().setModified(True)

        initial_count = tab_widget.count()
        tab_widget.open_file(str(test_file))

        # Should have created a new tab since current was modified
        assert tab_widget.count() == initial_count + 1

    def test_open_file_creates_new_when_has_path(self, tab_widget, tmp_path):
        """Test that a new tab is created when current tab has a file."""
        test_file1 = tmp_path / "test1.txt"
        test_file1.write_text("Content 1")
        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("Content 2")

        tab_widget.open_file(str(test_file1))
        initial_count = tab_widget.count()
        tab_widget.open_file(str(test_file2))

        assert tab_widget.count() == initial_count + 1


class TestDialogInteractions:
    """Test dialog-based interactions with mocking."""

    def test_open_file_with_dialog(self, tab_widget, tmp_path):
        """Test opening file via dialog."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Dialog content")

        with patch('src.tab_widget.QFileDialog.getOpenFileName') as mock_dialog:
            mock_dialog.return_value = (str(test_file), "All Files (*)")
            editor = tab_widget.open_file()
            assert editor is not None
            assert editor.toPlainText() == "Dialog content"

    def test_open_file_dialog_cancelled(self, tab_widget):
        """Test open file dialog cancelled."""
        with patch('src.tab_widget.QFileDialog.getOpenFileName') as mock_dialog:
            mock_dialog.return_value = ("", "")
            result = tab_widget.open_file()
            assert result is None

    def test_save_current_as_with_dialog(self, tab_widget, tmp_path):
        """Test save as via dialog."""
        test_file = tmp_path / "saved.txt"
        editor = tab_widget.current_editor()
        editor.setPlainText("Content to save")

        with patch('src.tab_widget.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = (str(test_file), "All Files (*)")
            result = tab_widget.save_current_as()
            assert result is True
            assert test_file.read_text() == "Content to save"

    def test_save_current_as_dialog_cancelled(self, tab_widget):
        """Test save as dialog cancelled."""
        with patch('src.tab_widget.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ("", "")
            result = tab_widget.save_current_as()
            assert result is False

    def test_close_tab_modified_save(self, tab_widget, tmp_path):
        """Test closing modified tab with save."""
        test_file = tmp_path / "modified.txt"
        editor = tab_widget.current_editor()
        editor.setPlainText("Modified content")
        editor.document().setModified(True)

        with patch('src.tab_widget.QMessageBox.question') as mock_msg, \
             patch('src.tab_widget.QFileDialog.getSaveFileName') as mock_save:
            mock_msg.return_value = QMessageBox.StandardButton.Save
            mock_save.return_value = (str(test_file), "All Files (*)")

            result = tab_widget.close_tab(0)
            assert result is True
            assert test_file.read_text() == "Modified content"

    def test_close_tab_modified_discard(self, tab_widget):
        """Test closing modified tab with discard."""
        editor = tab_widget.current_editor()
        editor.setPlainText("Modified content")
        editor.document().setModified(True)

        with patch('src.tab_widget.QMessageBox.question') as mock_msg:
            mock_msg.return_value = QMessageBox.StandardButton.Discard
            result = tab_widget.close_tab(0)
            assert result is True

    def test_close_tab_modified_cancel(self, tab_widget):
        """Test closing modified tab with cancel."""
        tab_widget.new_tab()  # Add another tab first
        editor = tab_widget.widget(0)
        editor.setPlainText("Modified content")
        editor.document().setModified(True)

        with patch('src.tab_widget.QMessageBox.question') as mock_msg:
            mock_msg.return_value = QMessageBox.StandardButton.Cancel
            result = tab_widget.close_tab(0)
            assert result is False

    def test_close_tab_save_fails(self, tab_widget):
        """Test closing modified tab when save fails."""
        tab_widget.new_tab()
        editor = tab_widget.widget(0)
        editor.setPlainText("Modified content")
        editor.document().setModified(True)

        with patch('src.tab_widget.QMessageBox.question') as mock_msg, \
             patch('src.tab_widget.QFileDialog.getSaveFileName') as mock_save:
            mock_msg.return_value = QMessageBox.StandardButton.Save
            mock_save.return_value = ("", "")  # Cancelled save dialog
            result = tab_widget.close_tab(0)
            assert result is False

    def test_close_all_tabs_with_modified(self, tab_widget):
        """Test close all tabs stops on cancel."""
        tab_widget.new_tab()
        editor = tab_widget.widget(0)
        editor.setPlainText("Modified")
        editor.document().setModified(True)

        with patch('src.tab_widget.QMessageBox.question') as mock_msg:
            mock_msg.return_value = QMessageBox.StandardButton.Cancel
            result = tab_widget.close_all_tabs()
            assert result is False


class TestOpenFileWithContent:
    """Test open_file_with_content functionality."""

    def test_open_file_with_content_new_tab(self, tab_widget, tmp_path):
        """Test open_file_with_content creates new tab with content."""
        # First, fill the current tab so it can't be reused
        current = tab_widget.current_editor()
        current.setPlainText("Existing content")
        current.document().setModified(True)

        test_path = str(tmp_path / "synced.txt")
        editor = tab_widget.open_file_with_content(test_path, "Synced content", modified=True)

        assert editor is not None
        assert editor.toPlainText() == "Synced content"
        assert editor.file_path == test_path
        assert editor.is_modified is True

    def test_open_file_with_content_reuses_empty_tab(self, tab_widget, tmp_path):
        """Test open_file_with_content reuses empty untitled tab."""
        # Current tab should be empty and untitled
        initial_count = tab_widget.count()

        test_path = str(tmp_path / "reused.txt")
        editor = tab_widget.open_file_with_content(test_path, "Reused content", modified=False)

        assert editor is not None
        assert editor.toPlainText() == "Reused content"
        assert tab_widget.count() == initial_count  # No new tab created

    def test_open_file_with_content_existing_path(self, tab_widget, tmp_path):
        """Test open_file_with_content returns existing editor if path already open."""
        test_path = str(tmp_path / "existing.txt")

        # Open with content first
        editor1 = tab_widget.open_file_with_content(test_path, "First content")

        # Open same path again - should return existing
        editor2 = tab_widget.open_file_with_content(test_path, "Different content")

        assert editor1 is editor2
        # Content should NOT change since we found existing
        assert editor1.toPlainText() == "First content"

    def test_open_file_with_content_creates_new_when_current_has_path(self, tab_widget, tmp_path):
        """Test that a new tab is created when current tab has a file path."""
        file1 = tmp_path / "file1.txt"
        file1.write_text("File 1")

        # Open first file
        tab_widget.open_file(str(file1))
        initial_count = tab_widget.count()

        # Open with content - should create new tab since current has path
        editor = tab_widget.open_file_with_content(
            str(tmp_path / "file2.txt"),
            "File 2 content"
        )

        assert editor is not None
        assert tab_widget.count() == initial_count + 1
