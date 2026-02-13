"""Tests for multi-file find and replace functionality."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.multi_file_find import MultiFileFindDialog, SearchResult
from src.split_container import SplitContainer
from src.main_window import MainWindow


@pytest.fixture(scope="session")
def app():
    """Create QApplication instance."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def main_window(app):
    """Create MainWindow instance."""
    window = MainWindow()
    yield window
    window.deleteLater()


@pytest.fixture
def dialog(main_window):
    """Create MultiFileFindDialog instance."""
    dlg = MultiFileFindDialog(main_window.split_container, main_window)
    yield dlg
    dlg.deleteLater()


def test_dialog_creation(dialog):
    """Test that dialog is created successfully."""
    assert dialog is not None
    assert dialog.windowTitle() == "Find in Files"
    assert dialog.find_input is not None
    assert dialog.replace_input is not None


def test_search_result_creation():
    """Test SearchResult creation."""
    result = SearchResult(
        file_path="/path/to/file.txt",
        line_number=10,
        line_text="This is a test line",
        match_start=10,
        match_end=14
    )
    assert result.file_path == "/path/to/file.txt"
    assert result.line_number == 10
    assert result.line_text == "This is a test line"
    assert result.match_start == 10
    assert result.match_end == 14


def test_search_in_text_basic(dialog):
    """Test basic text search."""
    text = "Hello world\nThis is a test\nHello again"
    results = dialog._search_in_text(text, "Hello", "test_file.txt")
    
    assert len(results) == 2
    assert results[0].line_number == 1
    assert results[1].line_number == 3


def test_search_in_text_case_sensitive(dialog):
    """Test case-sensitive search."""
    text = "Hello world\nhello again\nHELLO there"
    
    # Case insensitive
    dialog.case_sensitive_cb.setChecked(False)
    results = dialog._search_in_text(text, "hello", "test_file.txt")
    assert len(results) == 3
    
    # Case sensitive
    dialog.case_sensitive_cb.setChecked(True)
    results = dialog._search_in_text(text, "hello", "test_file.txt")
    assert len(results) == 1
    assert results[0].line_number == 2


def test_search_whole_word(dialog):
    """Test whole word search."""
    text = "test testing tested\ntest\ntestable"
    
    # Not whole word
    dialog.whole_word_cb.setChecked(False)
    results = dialog._search_in_text(text, "test", "test_file.txt")
    assert len(results) == 5  # Matches in testing, tested, test, testable
    
    # Whole word
    dialog.whole_word_cb.setChecked(True)
    results = dialog._search_in_text(text, "test", "test_file.txt")
    assert len(results) == 2  # Only standalone "test"


def test_is_whole_word(dialog):
    """Test whole word detection."""
    text = "hello world"
    
    # "hello" at start is whole word
    assert dialog._is_whole_word(text, 0, 5) is True
    
    # "world" at end is whole word
    assert dialog._is_whole_word(text, 6, 5) is True
    
    # Middle of word is not whole word
    text2 = "testing"
    assert dialog._is_whole_word(text2, 1, 3) is False  # "est"


def test_get_open_tabs(dialog, main_window):
    """Test getting open tabs."""
    # Create some tabs with content
    editor1 = main_window.split_container.current_editor()
    editor1.setPlainText("Content 1")
    
    main_window.split_container.new_tab()
    editor2 = main_window.split_container.current_editor()
    editor2.setPlainText("Content 2")
    
    files = dialog._get_open_tabs()
    assert len(files) >= 2


def test_replace_in_text_simple(dialog):
    """Test simple text replacement."""
    text = "Hello world\nHello again"
    results = [
        SearchResult("test.txt", 1, "Hello world", 0, 5),
        SearchResult("test.txt", 2, "Hello again", 0, 5)
    ]
    
    new_text = dialog._replace_in_text(text, results, "Hello", "Hi")
    assert new_text == "Hi world\nHi again"


def test_replace_in_text_multiple_per_line(dialog):
    """Test replacement with multiple matches per line."""
    text = "test test test"
    results = [
        SearchResult("test.txt", 1, "test test test", 0, 4),
        SearchResult("test.txt", 1, "test test test", 5, 9),
        SearchResult("test.txt", 1, "test test test", 10, 14)
    ]
    
    new_text = dialog._replace_in_text(text, results, "test", "TEST")
    assert new_text == "TEST TEST TEST"


def test_find_editor_for_file(dialog, main_window, tmp_path):
    """Test finding an open editor for a file."""
    # Create a temp file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Open it
    editor = main_window.split_container.open_file(str(test_file))
    
    # Find it
    found_editor = dialog._find_editor_for_file(str(test_file))
    assert found_editor is editor


def test_search_no_matches(dialog):
    """Test search with no matches."""
    text = "Hello world"
    results = dialog._search_in_text(text, "xyz", "test_file.txt")
    assert len(results) == 0


def test_search_empty_text(dialog):
    """Test search in empty text."""
    text = ""
    results = dialog._search_in_text(text, "test", "test_file.txt")
    assert len(results) == 0


def test_search_multiline_matches(dialog):
    """Test search across multiple lines."""
    text = "Line 1: test\nLine 2: test\nLine 3: testing\nLine 4: test"
    dialog.whole_word_cb.setChecked(True)
    results = dialog._search_in_text(text, "test", "test_file.txt")
    
    # Should find 3 matches (not "testing")
    assert len(results) == 3
    assert results[0].line_number == 1
    assert results[1].line_number == 2
    assert results[2].line_number == 4


def test_replace_with_longer_text(dialog):
    """Test replacement with longer text."""
    text = "a b c"
    results = [SearchResult("test.txt", 1, "a b c", 2, 3)]
    
    new_text = dialog._replace_in_text(text, results, "b", "longer")
    assert new_text == "a longer c"


def test_replace_with_empty_text(dialog):
    """Test replacement with empty string (deletion)."""
    text = "Hello world"
    results = [SearchResult("test.txt", 1, "Hello world", 6, 11)]

    new_text = dialog._replace_in_text(text, results, "world", "")
    assert new_text == "Hello "


def test_find_all_no_text(dialog):
    """Test find all with no search text."""
    dialog.find_input.setText("")
    dialog.find_all()
    assert dialog.status_label.text() == "Please enter search text"


def test_find_all_no_files(dialog):
    """Test find all with no files to search."""
    dialog.directory_radio.setChecked(True)
    dialog.directory_input.setText("/nonexistent/directory")
    dialog.find_input.setText("test")
    dialog.find_all()
    assert dialog.status_label.text() == "No files to search"


def test_find_all_no_matches(dialog, main_window):
    """Test find all with no matches."""
    editor = main_window.split_container.current_editor()
    editor.setPlainText("Hello world")

    dialog.find_input.setText("xyz")
    dialog.find_all()
    assert "No matches found" in dialog.status_label.text()


def test_find_all_with_matches(dialog, main_window):
    """Test find all with matches."""
    editor = main_window.split_container.current_editor()
    editor.setPlainText("test test test")

    dialog.find_input.setText("test")
    dialog.find_all()
    assert "3 matches" in dialog.status_label.text()


def test_scope_change_enables_browse(dialog):
    """Test that scope change enables browse button."""
    dialog.directory_radio.setChecked(True)
    assert dialog.directory_input.isEnabled()
    assert dialog.browse_btn.isEnabled()

    dialog.open_tabs_radio.setChecked(True)
    assert not dialog.directory_input.isEnabled()
    assert not dialog.browse_btn.isEnabled()


def test_display_results(dialog, main_window):
    """Test results are displayed in tree."""
    editor = main_window.split_container.current_editor()
    editor.setPlainText("test line")

    dialog.find_input.setText("test")
    dialog.find_all()

    assert dialog.results_tree.topLevelItemCount() > 0


def test_replace_selected_no_selection(dialog):
    """Test replace selected with no selection."""
    dialog.replace_selected()
    assert "No results selected" in dialog.status_label.text()


def test_replace_all_no_results(dialog):
    """Test replace all with no results."""
    dialog.results = []
    dialog.replace_all()
    assert "No results to replace" in dialog.status_label.text()


def test_get_directory_files_nonexistent(dialog):
    """Test get_directory_files with nonexistent directory."""
    dialog.directory_input.setText("/nonexistent/path")
    files = dialog._get_directory_files()
    assert files == []


def test_get_directory_files_empty(dialog):
    """Test get_directory_files with empty directory input."""
    dialog.directory_input.setText("")
    files = dialog._get_directory_files()
    assert files == []


def test_find_editor_for_file_not_found(dialog, main_window):
    """Test find_editor_for_file when file is not open."""
    editor = dialog._find_editor_for_file("/nonexistent/file.txt")
    assert editor is None


def test_replace_case_insensitive(dialog):
    """Test case insensitive replacement."""
    text = "Hello World"
    results = [SearchResult("test.txt", 1, "Hello World", 0, 5)]

    dialog.case_sensitive_cb.setChecked(False)
    new_text = dialog._replace_in_text(text, results, "hello", "Hi")
    assert new_text == "Hi World"


def test_replace_case_sensitive(dialog):
    """Test case sensitive replacement."""
    text = "Hello World"
    results = [SearchResult("test.txt", 1, "Hello World", 0, 5)]

    dialog.case_sensitive_cb.setChecked(True)
    new_text = dialog._replace_in_text(text, results, "Hello", "Hi")
    assert new_text == "Hi World"


def test_perform_replacements_in_editor(dialog, main_window, tmp_path):
    """Test performing replacements in open editor."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    editor = main_window.split_container.open_file(str(test_file))
    results = [SearchResult(str(test_file), 1, "test content", 0, 4)]

    dialog.case_sensitive_cb.setChecked(False)
    count = dialog._perform_replacements({str(test_file): results}, "test", "TEST")
    assert count == 1
    assert "TEST" in editor.toPlainText()


def test_get_open_tabs_multiple(dialog, main_window):
    """Test getting multiple open tabs."""
    main_window.split_container.new_tab()
    main_window.split_container.new_tab()

    files = dialog._get_open_tabs()
    assert len(files) >= 2


def test_get_directory_files_with_files(dialog, tmp_path):
    """Test getting files from a directory with text files."""
    # Create some test files
    (tmp_path / "test.txt").write_text("Test content")
    (tmp_path / "test.py").write_text("print('hello')")
    (tmp_path / "test.md").write_text("# Markdown")

    dialog.directory_input.setText(str(tmp_path))
    files = dialog._get_directory_files()
    assert len(files) >= 3


def test_find_all_in_directory(dialog, tmp_path):
    """Test finding in directory files."""
    # Create test file
    (tmp_path / "test.txt").write_text("test content here")

    dialog.directory_radio.setChecked(True)
    dialog.directory_input.setText(str(tmp_path))
    dialog.find_input.setText("test")
    dialog.find_all()

    assert "1 match" in dialog.status_label.text()


def test_result_double_click_file_open(dialog, main_window, tmp_path):
    """Test double-clicking a result opens the file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content\nline 2")

    # Open the file first
    main_window.split_container.open_file(str(test_file))

    # Search for content
    dialog.find_input.setText("test")
    dialog.find_all()

    # Get a result item
    if dialog.results_tree.topLevelItemCount() > 0:
        file_item = dialog.results_tree.topLevelItem(0)
        if file_item.childCount() > 0:
            match_item = file_item.child(0)
            dialog._on_result_double_clicked(match_item, 0)


def test_result_double_click_file_not_open(dialog, main_window, tmp_path):
    """Test double-clicking result when file is not open."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Search in directory
    dialog.directory_radio.setChecked(True)
    dialog.directory_input.setText(str(tmp_path))
    dialog.find_input.setText("test")
    dialog.find_all()

    # Get a result item and click it
    if dialog.results_tree.topLevelItemCount() > 0:
        file_item = dialog.results_tree.topLevelItem(0)
        if file_item.childCount() > 0:
            match_item = file_item.child(0)
            dialog._on_result_double_clicked(match_item, 0)


def test_result_double_click_non_result_item(dialog, main_window):
    """Test double-clicking non-result item does nothing."""
    from PyQt6.QtWidgets import QTreeWidgetItem

    # Create a dummy item without result data
    item = QTreeWidgetItem()
    dialog._on_result_double_clicked(item, 0)
    # Should not crash


def test_find_single_match_message(dialog, main_window):
    """Test status message for single match."""
    editor = main_window.split_container.current_editor()
    editor.setPlainText("unique text")

    dialog.find_input.setText("unique")
    dialog.find_all()

    assert "1 match" in dialog.status_label.text()
    assert "1 file" in dialog.status_label.text()


def test_browse_directory_dialog(dialog, tmp_path):
    """Test browse directory dialog."""
    with patch('src.multi_file_find.QFileDialog.getExistingDirectory') as mock_dialog:
        mock_dialog.return_value = str(tmp_path)
        dialog._browse_directory()
        assert dialog.directory_input.text() == str(tmp_path)


def test_browse_directory_cancelled(dialog):
    """Test browse directory dialog cancelled."""
    dialog.directory_input.setText("/original/path")
    with patch('src.multi_file_find.QFileDialog.getExistingDirectory') as mock_dialog:
        mock_dialog.return_value = ""
        dialog._browse_directory()
        # Should keep original path
        assert dialog.directory_input.text() == "/original/path"


def test_replace_all_with_confirmation(dialog, main_window, tmp_path):
    """Test replace all with confirmation dialog."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test test test")

    editor = main_window.split_container.open_file(str(test_file))

    dialog.find_input.setText("test")
    dialog.replace_input.setText("TEST")
    dialog.find_all()

    with patch('src.multi_file_find.QMessageBox.question') as mock_msg:
        mock_msg.return_value = QMessageBox.StandardButton.Yes
        dialog.replace_all()
        assert "TEST" in editor.toPlainText()


def test_replace_all_cancelled(dialog, main_window, tmp_path):
    """Test replace all cancelled."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test test test")

    editor = main_window.split_container.open_file(str(test_file))

    dialog.find_input.setText("test")
    dialog.replace_input.setText("TEST")
    dialog.find_all()

    with patch('src.multi_file_find.QMessageBox.question') as mock_msg:
        mock_msg.return_value = QMessageBox.StandardButton.No
        dialog.replace_all()
        # Should not be replaced
        assert "test" in editor.toPlainText()


def test_replace_selected_with_results(dialog, main_window, tmp_path):
    """Test replace selected items."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content here")

    editor = main_window.split_container.open_file(str(test_file))

    dialog.find_input.setText("test")
    dialog.replace_input.setText("TEST")
    dialog.find_all()

    # Select an item
    if dialog.results_tree.topLevelItemCount() > 0:
        file_item = dialog.results_tree.topLevelItem(0)
        if file_item.childCount() > 0:
            match_item = file_item.child(0)
            match_item.setSelected(True)

            dialog.replace_selected()
            assert "TEST" in editor.toPlainText()


def test_perform_replacements_in_file(dialog, tmp_path):
    """Test performing replacements in file on disk."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    results = [SearchResult(str(test_file), 1, "test content", 0, 4)]
    dialog.case_sensitive_cb.setChecked(False)

    count = dialog._perform_replacements({str(test_file): results}, "test", "TEST")
    assert count == 1
    assert test_file.read_text() == "TEST content"


def test_perform_replacements_file_error(dialog, tmp_path):
    """Test replacement error handling."""
    test_file = tmp_path / "readonly.txt"
    test_file.write_text("test content")

    results = [SearchResult(str(test_file), 1, "test content", 0, 4)]

    # Make file read-only
    test_file.chmod(0o444)

    with patch('src.multi_file_find.QMessageBox.warning') as mock_warn:
        try:
            dialog._perform_replacements({str(test_file): results}, "test", "TEST")
        finally:
            test_file.chmod(0o644)  # Restore permissions


def test_display_results_with_path(dialog, main_window, tmp_path):
    """Test display results with actual file path."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    dialog.directory_radio.setChecked(True)
    dialog.directory_input.setText(str(tmp_path))
    dialog.find_input.setText("test")
    dialog.find_all()

    # Check that results are displayed
    assert dialog.results_tree.topLevelItemCount() > 0


def test_on_result_double_click_opens_file(dialog, main_window, tmp_path):
    """Test double-clicking result opens and navigates to file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line 1\ntest content\nline 3")

    dialog.directory_radio.setChecked(True)
    dialog.directory_input.setText(str(tmp_path))
    dialog.find_input.setText("test")
    dialog.find_all()

    # Get result item and double-click
    if dialog.results_tree.topLevelItemCount() > 0:
        file_item = dialog.results_tree.topLevelItem(0)
        if file_item.childCount() > 0:
            match_item = file_item.child(0)
            dialog._on_result_double_clicked(match_item, 0)

            # File should be opened
            editor = main_window.split_container.current_editor()
            assert "test content" in editor.toPlainText()
