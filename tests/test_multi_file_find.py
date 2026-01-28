"""Tests for multi-file find and replace functionality."""

import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
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
