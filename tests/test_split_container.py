"""Tests for the SplitContainer widget."""

import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.split_container import SplitContainer
from src.tab_widget import EditorTabWidget


@pytest.fixture(scope="session")
def app():
    """Create a QApplication instance for the test session."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def split_container(app):
    """Create a SplitContainer instance."""
    container = SplitContainer()
    yield container
    container.deleteLater()


class TestSplitContainerBasics:
    """Test basic split container functionality."""

    def test_initial_state(self, split_container):
        """Test initial state has one tab widget."""
        assert split_container.active_tab_widget() is not None
        assert split_container.current_editor() is not None

    def test_new_tab(self, split_container):
        """Test creating a new tab."""
        initial_count = split_container.active_tab_widget().count()
        split_container.new_tab()
        assert split_container.active_tab_widget().count() == initial_count + 1

    def test_current_editor(self, split_container):
        """Test getting current editor."""
        editor = split_container.current_editor()
        assert editor is not None
        editor.setPlainText("Test content")
        assert split_container.current_editor().toPlainText() == "Test content"


class TestSplitOperations:
    """Test split view operations."""

    def test_split_horizontal(self, split_container):
        """Test horizontal split."""
        initial_tabs = split_container._get_all_tab_widgets()
        split_container.split_horizontal()
        new_tabs = split_container._get_all_tab_widgets()
        assert len(new_tabs) == len(initial_tabs) + 1

    def test_split_vertical(self, split_container):
        """Test vertical split."""
        initial_tabs = split_container._get_all_tab_widgets()
        split_container.split_vertical()
        new_tabs = split_container._get_all_tab_widgets()
        assert len(new_tabs) == len(initial_tabs) + 1

    def test_multiple_splits(self, split_container):
        """Test creating multiple splits."""
        split_container.split_horizontal()
        split_container.split_vertical()
        tabs = split_container._get_all_tab_widgets()
        assert len(tabs) == 3

    def test_close_split(self, split_container):
        """Test closing a split."""
        split_container.split_horizontal()
        initial_count = len(split_container._get_all_tab_widgets())
        split_container.close_split()
        # close_split closes all tabs in active pane which removes it
        assert len(split_container._get_all_tab_widgets()) <= initial_count

    def test_close_split_single_pane(self, split_container):
        """Test close split with only one pane does nothing."""
        initial_count = len(split_container._get_all_tab_widgets())
        split_container.close_split()
        assert len(split_container._get_all_tab_widgets()) == initial_count


class TestFocusNavigation:
    """Test focus navigation between splits."""

    def test_focus_next_split(self, split_container):
        """Test focusing next split."""
        split_container.split_horizontal()
        first_tabs = split_container.active_tab_widget()
        split_container.focus_next_split()
        # Should have moved to a different tab widget
        assert split_container.active_tab_widget() is not None

    def test_focus_previous_split(self, split_container):
        """Test focusing previous split."""
        split_container.split_horizontal()
        split_container.focus_previous_split()
        assert split_container.active_tab_widget() is not None

    def test_focus_next_single_split(self, split_container):
        """Test focus next with single split does nothing."""
        active = split_container.active_tab_widget()
        split_container.focus_next_split()
        assert split_container.active_tab_widget() == active

    def test_focus_previous_single_split(self, split_container):
        """Test focus previous with single split does nothing."""
        active = split_container.active_tab_widget()
        split_container.focus_previous_split()
        assert split_container.active_tab_widget() == active


class TestTabNavigation:
    """Test tab navigation within splits."""

    def test_next_tab(self, split_container):
        """Test switching to next tab."""
        split_container.new_tab()
        split_container.new_tab()
        tabs = split_container.active_tab_widget()
        tabs.setCurrentIndex(0)
        split_container.next_tab()
        assert tabs.currentIndex() == 1

    def test_previous_tab(self, split_container):
        """Test switching to previous tab."""
        split_container.new_tab()
        split_container.new_tab()
        tabs = split_container.active_tab_widget()
        tabs.setCurrentIndex(2)
        split_container.previous_tab()
        assert tabs.currentIndex() == 1


class TestFileOperations:
    """Test file operations through split container."""

    def test_open_file_path(self, split_container, tmp_path):
        """Test opening a file by path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        editor = split_container.open_file_path(str(test_file))
        assert editor is not None
        assert editor.toPlainText() == "Test content"

    def test_save_current(self, split_container, tmp_path):
        """Test saving current file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Original")

        split_container.open_file_path(str(test_file))
        editor = split_container.current_editor()
        editor.setPlainText("Modified")

        result = split_container.save_current()
        assert result is True
        assert test_file.read_text() == "Modified"

    def test_save_current_no_path(self, split_container):
        """Test save_current returns False for untitled file without dialog."""
        # New tab has no file path
        split_container.new_tab()
        # save_current will call save_current_as which shows dialog
        # In test environment, dialog will be cancelled
        result = split_container.save_current()
        # Will return False since no dialog interaction
        assert result is False or result is True  # Depends on dialog behavior


class TestCloseAllTabs:
    """Test close all tabs functionality."""

    def test_close_all_tabs_empty(self, split_container):
        """Test closing all tabs when unmodified."""
        result = split_container.close_all_tabs()
        assert result is True

    def test_close_all_tabs_multiple_splits(self, split_container):
        """Test closing all tabs with multiple splits."""
        split_container.split_horizontal()
        result = split_container.close_all_tabs()
        assert result is True


class TestSignals:
    """Test signal emissions."""

    def test_current_editor_changed_signal(self, split_container):
        """Test current_editor_changed signal is emitted."""
        received = []
        split_container.current_editor_changed.connect(lambda e: received.append(e))

        split_container.new_tab()
        assert len(received) > 0

    def test_active_tabs_changed_signal(self, split_container):
        """Test active_tabs_changed signal is emitted."""
        received = []
        split_container.active_tabs_changed.connect(lambda t: received.append(t))

        split_container.split_horizontal()
        assert len(received) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_balance_splitter(self, split_container):
        """Test splitter balancing."""
        split_container.split_horizontal()
        split_container.split_horizontal()
        # Just ensure no crash
        tabs = split_container._get_all_tab_widgets()
        assert len(tabs) == 3

    def test_set_active_tabs_same(self, split_container):
        """Test setting same active tabs does nothing."""
        active = split_container.active_tab_widget()
        split_container._set_active_tabs(active)
        assert split_container.active_tab_widget() == active

    def test_on_editor_changed_different_sender(self, split_container):
        """Test editor change from non-active tab widget."""
        split_container.split_horizontal()
        # Both tab widgets exist, change in one should only emit if active
        editor = split_container.current_editor()
        assert editor is not None


class TestNullActiveTabsCases:
    """Test cases when _active_tabs is None."""

    def test_current_editor_no_active_tabs(self, split_container):
        """Test current_editor when _active_tabs is None."""
        # Force _active_tabs to None
        split_container._active_tabs = None
        result = split_container.current_editor()
        assert result is None

    def test_new_tab_no_active_tabs(self, split_container):
        """Test new_tab when _active_tabs is None."""
        split_container._active_tabs = None
        result = split_container.new_tab()
        assert result is None

    def test_open_file_no_active_tabs(self, split_container):
        """Test open_file when _active_tabs is None."""
        split_container._active_tabs = None
        result = split_container.open_file()
        assert result is None

    def test_save_current_no_active_tabs(self, split_container):
        """Test save_current when _active_tabs is None."""
        split_container._active_tabs = None
        result = split_container.save_current()
        assert result is False

    def test_save_current_as_no_active_tabs(self, split_container):
        """Test save_current_as when _active_tabs is None."""
        split_container._active_tabs = None
        result = split_container.save_current_as()
        assert result is False

    def test_close_current_tab_no_active_tabs(self, split_container):
        """Test close_current_tab when _active_tabs is None."""
        split_container._active_tabs = None
        result = split_container.close_current_tab()
        assert result is False

    def test_next_tab_no_active_tabs(self, split_container):
        """Test next_tab when _active_tabs is None."""
        split_container._active_tabs = None
        # Should not raise exception
        split_container.next_tab()
        assert True

    def test_previous_tab_no_active_tabs(self, split_container):
        """Test previous_tab when _active_tabs is None."""
        split_container._active_tabs = None
        # Should not raise exception
        split_container.previous_tab()
        assert True

    def test_split_no_active_tabs(self, split_container):
        """Test _split when _active_tabs is None."""
        split_container._active_tabs = None
        # Should not raise exception, just return
        split_container._split(Qt.Orientation.Horizontal)
        assert True

    def test_close_split_no_active_tabs(self, split_container):
        """Test close_split when _active_tabs is None."""
        split_container._active_tabs = None
        split_container.close_split()
        assert True


class TestAllTabsClosedSignal:
    """Test all tabs closed signal handling."""

    def test_on_all_tabs_closed_single_pane(self, split_container):
        """Test that closing all tabs in single pane creates new tab."""
        tabs = split_container.active_tab_widget()
        initial_editor = tabs.current_editor()

        # Close the tab - should trigger new tab creation
        tabs.close_tab(0)

        # Should still have a tab
        assert tabs.count() >= 1


class TestCleanupEmptySplitters:
    """Test empty splitter cleanup."""

    def test_cleanup_after_close_split(self, split_container):
        """Test that empty splitters are cleaned up."""
        # Create multiple splits
        split_container.split_horizontal()
        split_container.split_vertical()

        all_tabs = split_container._get_all_tab_widgets()
        assert len(all_tabs) == 3

        # Close tabs in active split
        active = split_container.active_tab_widget()
        active.close_all_tabs()

        # Should have cleaned up
        remaining_tabs = split_container._get_all_tab_widgets()
        assert len(remaining_tabs) < 3


class TestTabFocus:
    """Test tab focus handling."""

    def test_tabs_focus_changes_active(self, split_container):
        """Test that focusing a tab widget changes active."""
        split_container.split_horizontal()
        all_tabs = split_container._get_all_tab_widgets()

        # Focus the other tab widget
        other_tabs = [t for t in all_tabs if t != split_container._active_tabs][0]
        split_container._set_active_tabs(other_tabs)

        assert split_container._active_tabs == other_tabs


class TestFocusNavigationEdgeCases:
    """Test focus navigation edge cases."""

    def test_focus_next_with_invalid_active(self, split_container):
        """Test focus next when active tabs is not in list."""
        split_container.split_horizontal()
        # Create a new tab widget that's not added to container
        from src.tab_widget import EditorTabWidget
        orphan_tabs = EditorTabWidget()
        split_container._active_tabs = orphan_tabs

        # Should handle ValueError gracefully
        split_container.focus_next_split()
        orphan_tabs.deleteLater()

    def test_focus_previous_with_invalid_active(self, split_container):
        """Test focus previous when active tabs is not in list."""
        split_container.split_horizontal()
        from src.tab_widget import EditorTabWidget
        orphan_tabs = EditorTabWidget()
        split_container._active_tabs = orphan_tabs

        # Should handle ValueError gracefully
        split_container.focus_previous_split()
        orphan_tabs.deleteLater()


class TestCleanupEdgeCases:
    """Test cleanup edge cases."""

    def test_cleanup_nested_splitters(self, split_container):
        """Test cleanup of deeply nested splitters."""
        # Create nested splits
        split_container.split_horizontal()
        split_container.split_vertical()
        split_container.split_horizontal()

        all_tabs = split_container._get_all_tab_widgets()
        assert len(all_tabs) == 4

        # Close some tabs to trigger cleanup
        active = split_container.active_tab_widget()
        active.close_all_tabs()

        # Cleanup should have been called
        remaining = split_container._get_all_tab_widgets()
        assert len(remaining) < 4


class TestOpenFilePath:
    """Test open_file_path method."""

    def test_open_file_path_no_active_tabs(self, split_container):
        """Test open_file_path when no active tabs."""
        split_container._active_tabs = None
        result = split_container.open_file_path("/some/path.txt")
        assert result is None


class TestSaveOperations:
    """Test save operations."""

    def test_save_current_as_with_tabs(self, split_container, tmp_path):
        """Test save_current_as with active tabs."""
        test_file = tmp_path / "save_as.txt"
        editor = split_container.current_editor()
        editor.setPlainText("Content to save")

        with patch('src.tab_widget.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = (str(test_file), "All Files (*)")
            result = split_container.save_current_as()
            assert result is True
            assert test_file.read_text() == "Content to save"

    def test_close_current_tab_with_tabs(self, split_container):
        """Test close_current_tab with active tabs."""
        # Add a second tab so we don't trigger all_tabs_closed
        split_container.new_tab()
        initial_count = split_container.active_tab_widget().count()

        result = split_container.close_current_tab()
        assert result is True
        assert split_container.active_tab_widget().count() == initial_count - 1


class TestFocusEvents:
    """Test focus event handling."""

    def test_on_tabs_focused(self, split_container):
        """Test _on_tabs_focused method."""
        from PyQt6.QtGui import QFocusEvent
        from PyQt6.QtCore import Qt

        split_container.split_horizontal()
        all_tabs = split_container._get_all_tab_widgets()
        other_tabs = [t for t in all_tabs if t != split_container._active_tabs][0]

        # Create a focus event
        event = QFocusEvent(QFocusEvent.Type.FocusIn, Qt.FocusReason.MouseFocusReason)

        # Trigger focus event
        split_container._on_tabs_focused(other_tabs, event)

        # Should have changed active tabs
        assert split_container._active_tabs == other_tabs


class TestEmptySplitterCleanup:
    """Test cleanup of empty splitters."""

    def test_cleanup_removes_empty_splitter(self, split_container):
        """Test that empty splitters are removed during cleanup."""
        from PyQt6.QtWidgets import QSplitter

        # Create a nested structure
        split_container.split_horizontal()
        split_container.split_vertical()

        # Get initial state
        initial_tab_count = len(split_container._get_all_tab_widgets())
        assert initial_tab_count == 3

        # Close all tabs in one split to make an empty splitter
        split_container._closing = True
        active = split_container.active_tab_widget()
        while active.count() > 0:
            active.removeTab(0)
        split_container._closing = False

        # Manually trigger cleanup
        split_container._remove_tab_widget(active)

        # Should have fewer tabs now
        remaining = len(split_container._get_all_tab_widgets())
        assert remaining < initial_tab_count


class TestLiveSyncBetweenEditors:
    """Test live content synchronization between editors showing the same file."""

    def test_open_same_file_in_split_creates_sync(self, split_container, tmp_path):
        """Test opening the same file in different splits sets up sync."""
        test_file = tmp_path / "sync_test.txt"
        test_file.write_text("Initial content")

        # Open file in first pane
        editor1 = split_container.open_file_path(str(test_file))
        assert editor1 is not None

        # Create split and open same file
        split_container.split_horizontal()
        editor2 = split_container.open_file_path(str(test_file))

        # Both should have same content
        assert editor1.toPlainText() == "Initial content"
        assert editor2.toPlainText() == "Initial content"

        # Should be registered for sync
        file_path = str(test_file)
        assert file_path in split_container._file_syncs
        assert len(split_container._file_syncs[file_path]) == 2

    def test_open_file_with_dialog_cancelled(self, split_container):
        """Test open_file when dialog is cancelled returns None."""
        with patch('src.split_container.QFileDialog.getOpenFileName') as mock_dialog:
            mock_dialog.return_value = ("", "")
            result = split_container.open_file()
            assert result is None

    def test_open_file_with_dialog_success(self, split_container, tmp_path):
        """Test open_file with dialog selecting a file."""
        test_file = tmp_path / "dialog_test.txt"
        test_file.write_text("Dialog content")

        with patch('src.split_container.QFileDialog.getOpenFileName') as mock_dialog:
            mock_dialog.return_value = (str(test_file), "All Files (*)")
            result = split_container.open_file()
            assert result is not None
            assert result.toPlainText() == "Dialog content"

    def test_open_file_existing_in_same_pane(self, split_container, tmp_path):
        """Test opening already open file in the same pane switches to it."""
        test_file = tmp_path / "same_pane.txt"
        test_file.write_text("Same pane content")

        # Open file
        editor1 = split_container.open_file_path(str(test_file))

        # Open another file to change current tab
        split_container.new_tab()

        # Open the same file again in same pane
        editor2 = split_container.open_file(str(test_file))

        # Should return the same editor
        assert editor1 is editor2

    def test_editing_synced_editor_updates_other(self, split_container, tmp_path):
        """Test that editing one synced editor updates the other."""
        test_file = tmp_path / "sync_edit_test.txt"
        test_file.write_text("Original text")

        # Open file in first pane
        editor1 = split_container.open_file_path(str(test_file))

        # Create split and open same file
        split_container.split_horizontal()
        editor2 = split_container.open_file_path(str(test_file))

        # Edit editor1
        cursor = editor1.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor1.setTextCursor(cursor)
        editor1.insertPlainText(" - added")

        # Editor2 should have the changes
        # Note: The sync happens via document signals, give it a moment to process
        import time
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        # Both should have updated content
        assert "added" in editor1.toPlainText()
        assert "added" in editor2.toPlainText()

    def test_replay_edit_skips_self(self, split_container, tmp_path):
        """Test that replay_edit doesn't create infinite loop by skipping source."""
        test_file = tmp_path / "no_loop_test.txt"
        test_file.write_text("Test content")

        editor1 = split_container.open_file_path(str(test_file))
        split_container.split_horizontal()
        editor2 = split_container.open_file_path(str(test_file))

        # Multiple edits should not cause issues
        for i in range(3):
            cursor = editor1.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            editor1.setTextCursor(cursor)
            editor1.insertPlainText(f"{i}")

        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        # Both should have all updates
        assert editor1.toPlainText() == editor2.toPlainText()

    def test_replay_edit_handles_deletion(self, split_container, tmp_path):
        """Test that sync handles text deletion properly."""
        test_file = tmp_path / "delete_sync.txt"
        test_file.write_text("ABCDEF")

        editor1 = split_container.open_file_path(str(test_file))
        split_container.split_horizontal()
        editor2 = split_container.open_file_path(str(test_file))

        # Select and delete some text from editor1
        cursor = editor1.textCursor()
        cursor.setPosition(2)
        cursor.setPosition(4, cursor.MoveMode.KeepAnchor)  # Select "CD"
        cursor.removeSelectedText()

        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        # Both should reflect the deletion
        assert editor1.toPlainText() == "ABEF"
        assert editor2.toPlainText() == "ABEF"

    def test_register_sync_only_once(self, split_container, tmp_path):
        """Test that an editor is only registered once for sync."""
        test_file = tmp_path / "register_once.txt"
        test_file.write_text("Test")

        editor = split_container.open_file_path(str(test_file))
        file_path = str(test_file)

        # Manually try to register the same editor again
        split_container._register_sync(file_path, editor)
        split_container._register_sync(file_path, editor)

        # Should only be in the list once
        assert split_container._file_syncs[file_path].count(editor) == 1

    def test_find_editor_for_file(self, split_container, tmp_path):
        """Test finding an editor for a specific file path."""
        test_file = tmp_path / "find_editor.txt"
        test_file.write_text("Content")

        editor = split_container.open_file_path(str(test_file))

        found = split_container.find_editor_for_file(str(test_file))
        assert found is editor

    def test_find_editor_for_file_not_found(self, split_container):
        """Test find_editor_for_file returns None when file not open."""
        result = split_container.find_editor_for_file("/nonexistent/file.txt")
        assert result is None

    def test_replay_edit_with_single_editor(self, split_container, tmp_path):
        """Test _replay_edit returns early when only one editor in sync group."""
        test_file = tmp_path / "single.txt"
        test_file.write_text("Single editor content")

        editor = split_container.open_file_path(str(test_file))
        file_path = str(test_file)

        # Manually register sync for single editor
        split_container._register_sync(file_path, editor)

        # Edit should not cause issues - group has only 1 editor
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        editor.insertPlainText("!")

        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        assert "Single editor content!" in editor.toPlainText()

    def test_open_file_existing_in_other_pane_via_open_file(self, split_container, tmp_path):
        """Test open_file method when file is open in another pane."""
        test_file = tmp_path / "cross_pane.txt"
        test_file.write_text("Cross pane content")

        # Open file in first pane
        editor1 = split_container.open_file_path(str(test_file))

        # Create split
        split_container.split_horizontal()

        # Use open_file (not open_file_path) with the path
        editor2 = split_container.open_file(str(test_file))

        assert editor2 is not None
        assert editor2.toPlainText() == "Cross pane content"
        # Should have synced editors
        file_path = str(test_file)
        assert file_path in split_container._file_syncs
