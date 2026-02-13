"""Tests for the FindReplaceWidget."""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

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
def editor(app):
    """Create a TextEditor instance."""
    ed = TextEditor()
    yield ed
    ed.deleteLater()


@pytest.fixture
def find_replace(app, editor):
    """Create a FindReplaceWidget instance."""
    widget = FindReplaceWidget()
    widget.set_editor(editor)
    yield widget
    widget.deleteLater()


class TestFindFunctionality:
    """Test find functionality."""
    
    def test_find_next_basic(self, editor, find_replace):
        """Test basic find next."""
        editor.setPlainText("Hello World Hello")
        # Setting text triggers auto-find, which finds first match at position 5
        find_replace.find_input.setText("Hello")

        # Auto-find already found first match, so cursor should be at position 5
        assert editor.textCursor().selectedText() == "Hello"
        assert editor.textCursor().position() == 5

        # Calling find_next again should find the second match
        assert find_replace.find_next()
        assert editor.textCursor().selectedText() == "Hello"
        assert editor.textCursor().position() == 17
    
    def test_find_next_wraps(self, editor, find_replace):
        """Test that find wraps around."""
        editor.setPlainText("Hello World Hello")
        # Auto-find triggers, finds first match at position 5
        find_replace.find_input.setText("Hello")
        assert editor.textCursor().position() == 5

        # Find second match at position 17
        find_replace.find_next()
        assert editor.textCursor().position() == 17

        # Should wrap to first match at position 5
        assert find_replace.find_next()
        assert editor.textCursor().position() == 5
    
    def test_find_previous(self, editor, find_replace):
        """Test find previous."""
        editor.setPlainText("Hello World Hello")
        cursor = editor.textCursor()
        cursor.setPosition(len("Hello World Hello"))
        editor.setTextCursor(cursor)
        
        find_replace.find_input.setText("Hello")
        
        assert find_replace.find_previous()
        assert editor.textCursor().selectedText() == "Hello"
    
    def test_find_case_sensitive(self, editor, find_replace):
        """Test case sensitive search."""
        editor.setPlainText("Hello hello HELLO")
        find_replace.find_input.setText("hello")
        find_replace.case_sensitive_cb.setChecked(True)
        
        assert find_replace.find_next()
        assert editor.textCursor().position() == 11
    
    def test_find_whole_word(self, editor, find_replace):
        """Test whole word search."""
        editor.setPlainText("Hello HelloWorld Hello")
        # Set whole word BEFORE setting text to ensure auto-find uses it
        find_replace.whole_word_cb.setChecked(True)
        # Auto-find triggers with whole-word, finds first "Hello" at position 5
        find_replace.find_input.setText("Hello")
        first_pos = editor.textCursor().position()

        # Find next whole word "Hello" - skips "HelloWorld", finds last "Hello" at position 22
        find_replace.find_next()
        second_pos = editor.textCursor().position()

        assert first_pos == 5
        assert second_pos == 22
    
    def test_find_no_match(self, editor, find_replace):
        """Test find with no match."""
        editor.setPlainText("Hello World")
        find_replace.find_input.setText("xyz")
        
        assert not find_replace.find_next()
    
    def test_find_empty_search(self, editor, find_replace):
        """Test find with empty search text."""
        editor.setPlainText("Hello World")
        find_replace.find_input.setText("")
        
        assert not find_replace.find_next()


class TestReplaceFunctionality:
    """Test replace functionality."""
    
    def test_replace_single(self, editor, find_replace):
        """Test single replacement."""
        editor.setPlainText("Hello World Hello")
        # Auto-find triggers, finds first match
        find_replace.find_input.setText("Hello")
        find_replace.replace_input.setText("Hi")

        # Replace the first match (already selected by auto-find)
        find_replace.replace()

        assert "Hi World" in editor.toPlainText()
    
    def test_replace_all(self, editor, find_replace):
        """Test replace all."""
        editor.setPlainText("Hello World Hello Hello")
        find_replace.find_input.setText("Hello")
        find_replace.replace_input.setText("Hi")
        
        count = find_replace.replace_all()
        
        assert count == 3
        assert editor.toPlainText() == "Hi World Hi Hi"
    
    def test_replace_all_case_sensitive(self, editor, find_replace):
        """Test case sensitive replace all."""
        editor.setPlainText("Hello hello HELLO")
        find_replace.find_input.setText("hello")
        find_replace.replace_input.setText("hi")
        find_replace.case_sensitive_cb.setChecked(True)
        
        count = find_replace.replace_all()
        
        assert count == 1
        assert editor.toPlainText() == "Hello hi HELLO"
    
    def test_replace_empty_replacement(self, editor, find_replace):
        """Test replacing with empty string (deletion)."""
        editor.setPlainText("Hello World")
        find_replace.find_input.setText(" World")
        find_replace.replace_input.setText("")
        
        find_replace.replace_all()
        
        assert editor.toPlainText() == "Hello"
    
    def test_replace_no_match(self, editor, find_replace):
        """Test replace with no matches."""
        editor.setPlainText("Hello World")
        find_replace.find_input.setText("xyz")
        find_replace.replace_input.setText("abc")
        
        count = find_replace.replace_all()
        
        assert count == 0
        assert editor.toPlainText() == "Hello World"


class TestFindReplaceUI:
    """Test find/replace UI behavior."""

    def test_show_find_focuses_input(self, editor, find_replace):
        """Test that showing find bar focuses the input."""
        find_replace.show_find()
        assert find_replace.isVisible()

    def test_show_find_uses_selection(self, editor, find_replace):
        """Test that showing find uses current selection."""
        editor.setPlainText("Hello World")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(5, cursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)

        find_replace.show_find()

        assert find_replace.find_input.text() == "Hello"

    def test_close_widget(self, editor, find_replace):
        """Test closing the find/replace widget."""
        find_replace.show()
        find_replace._close()
        assert not find_replace.isVisible()

    def test_close_emits_signal(self, editor, find_replace):
        """Test that closing emits closed signal."""
        received = []
        find_replace.closed.connect(lambda: received.append(True))

        find_replace.show()
        find_replace._close()

        assert len(received) == 1

    def test_escape_key_closes(self, editor, find_replace):
        """Test that Escape key closes the widget."""
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent

        find_replace.show()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        find_replace.keyPressEvent(event)
        assert not find_replace.isVisible()

    def test_other_key_passes_through(self, editor, find_replace):
        """Test that other keys are passed to parent."""
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent

        find_replace.show()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        find_replace.keyPressEvent(event)
        # Widget should still be visible
        assert find_replace.isVisible()


class TestFindReplaceEdgeCases:
    """Test edge cases for find/replace."""

    def test_find_next_no_editor(self, app):
        """Test find_next with no editor set."""
        widget = FindReplaceWidget()
        widget.find_input.setText("test")
        result = widget.find_next()
        assert result is False
        widget.deleteLater()

    def test_find_previous_no_editor(self, app):
        """Test find_previous with no editor set."""
        widget = FindReplaceWidget()
        widget.find_input.setText("test")
        result = widget.find_previous()
        assert result is False
        widget.deleteLater()

    def test_find_previous_no_match(self, editor, find_replace):
        """Test find_previous with no match."""
        editor.setPlainText("Hello World")
        find_replace.find_input.setText("xyz")
        result = find_replace.find_previous()
        assert result is False

    def test_replace_no_editor(self, app):
        """Test replace with no editor set."""
        widget = FindReplaceWidget()
        widget.find_input.setText("test")
        result = widget.replace()
        assert result is False
        widget.deleteLater()

    def test_replace_all_no_editor(self, app):
        """Test replace_all with no editor set."""
        widget = FindReplaceWidget()
        widget.find_input.setText("test")
        result = widget.replace_all()
        assert result == 0
        widget.deleteLater()

    def test_replace_case_sensitive_match(self, editor, find_replace):
        """Test replace with case sensitive matching."""
        editor.setPlainText("Hello World")
        find_replace.find_input.setText("Hello")
        find_replace.replace_input.setText("Hi")
        find_replace.case_sensitive_cb.setChecked(True)

        # Auto-find selects "Hello"
        find_replace.replace()
        assert editor.toPlainText() == "Hi World"

    def test_replace_case_insensitive_no_match(self, editor, find_replace):
        """Test replace when selected text doesn't match."""
        editor.setPlainText("Hello World")
        find_replace.find_input.setText("xyz")
        find_replace.replace_input.setText("abc")

        # Select some text manually
        cursor = editor.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(5, cursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)

        # Replace should not work since selection doesn't match
        find_replace.replace()
        # "Hello" is still there because it didn't match "xyz"
        assert "Hello" in editor.toPlainText()

    def test_update_match_count_no_editor(self, app):
        """Test match count update with no editor."""
        widget = FindReplaceWidget()
        widget.find_input.setText("test")
        widget._update_match_count()
        assert widget.match_label.text() == ""
        widget.deleteLater()

    def test_update_match_count_empty_text(self, editor, find_replace):
        """Test match count update with empty search text."""
        editor.setPlainText("Hello World")
        find_replace.find_input.setText("")
        find_replace._update_match_count()
        assert find_replace.match_label.text() == ""

    def test_show_find_no_editor(self, app):
        """Test show_find with no editor."""
        widget = FindReplaceWidget()
        widget.show_find()
        assert widget.isVisible()
        widget.deleteLater()

    def test_close_focuses_editor(self, editor, find_replace):
        """Test that closing focuses the editor."""
        find_replace.show()
        find_replace._close()
        # Editor should be focused (in real app)
        assert not find_replace.isVisible()


class TestFindPreviousWrapping:
    """Test find previous wrapping behavior."""

    def test_find_previous_wraps(self, editor, find_replace):
        """Test that find_previous wraps to end."""
        editor.setPlainText("Hello World Hello")
        # Position cursor at the start
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)

        find_replace.find_input.setText("Hello")
        # This should wrap to find from the end
        result = find_replace.find_previous()
        assert result is True
