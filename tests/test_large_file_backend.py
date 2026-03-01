"""Tests for the LargeFileBackend mmap-based file handling."""

import os
import tempfile
import pytest

from src.large_file_backend import LargeFileBackend, _CompactPatches, WINDOW_LINES
import array


@pytest.fixture
def large_file(tmp_path):
    """Create a test file with known content."""
    path = tmp_path / "test_large.txt"
    lines = [f"Line {i}: some content here for testing\n" for i in range(500)]
    path.write_text("".join(lines))
    return str(path)


@pytest.fixture
def backend(large_file):
    """Create a LargeFileBackend instance."""
    be = LargeFileBackend(large_file)
    yield be
    be.close()


class TestLargeFileBackendInit:
    """Test backend initialization and line index building."""

    def test_total_lines(self, backend):
        """Test that total_lines returns correct count (500 lines + 1 for trailing newline offset)."""
        assert backend.total_lines == 501

    def test_file_path(self, backend, large_file):
        """Test file_path property."""
        assert backend.file_path == large_file

    def test_line_index_starts_at_zero(self, backend):
        """Test first line offset is 0."""
        assert backend._line_offsets[0] == 0


class TestGetWindowText:
    """Test windowed text retrieval."""

    def test_get_window_at_start(self, backend):
        """Test getting a window at the start of the file."""
        text, win_start, win_end = backend.get_window_text(0)
        assert win_start == 0
        assert win_end <= backend.total_lines
        assert "Line 0:" in text

    def test_get_window_at_middle(self, backend):
        """Test getting a window centered in the middle."""
        text, win_start, win_end = backend.get_window_text(250)
        assert "Line 250:" in text

    def test_get_window_at_end(self, backend):
        """Test getting a window at the end of the file."""
        text, win_start, win_end = backend.get_window_text(499)
        assert "Line 499:" in text

    def test_window_strips_trailing_newline(self, backend):
        """Test that trailing newline is stripped."""
        text, _, _ = backend.get_window_text(0)
        assert not text.endswith('\n')

    def test_window_covers_full_small_file(self, tmp_path):
        """Test that a small file is fully covered in one window."""
        path = tmp_path / "small.txt"
        lines = [f"Line {i}\n" for i in range(10)]
        path.write_text("".join(lines))
        be = LargeFileBackend(str(path))
        text, win_start, win_end = be.get_window_text(0)
        assert win_start == 0
        assert win_end == 11  # 10 lines + offset entry for trailing newline
        assert "Line 0" in text
        assert "Line 9" in text
        be.close()


class TestByteOffsetConversion:
    """Test byte offset <-> line number conversion."""

    def test_byte_offset_to_line_start(self, backend):
        """Test byte offset at file start maps to line 0."""
        assert backend.byte_offset_to_line(0) == 0

    def test_line_to_byte_offset_first_line(self, backend):
        """Test line 0 maps to byte 0."""
        assert backend.line_to_byte_offset(0) == 0

    def test_line_to_byte_offset_negative(self, backend):
        """Test negative line returns 0."""
        assert backend.line_to_byte_offset(-1) == 0

    def test_line_to_byte_offset_beyond_end(self, backend):
        """Test line beyond total returns file_size."""
        assert backend.line_to_byte_offset(99999) == backend._file_size

    def test_byte_offset_roundtrip(self, backend):
        """Test converting line->byte->line gives same line."""
        for line in [0, 10, 100, 250, 499]:
            byte_off = backend.line_to_byte_offset(line)
            back_line = backend.byte_offset_to_line(byte_off)
            assert back_line == line


class TestCountMatches:
    """Test match counting across the file."""

    def test_count_case_sensitive(self, backend):
        """Test case-sensitive count."""
        count = backend.count_matches("Line", case_sensitive=True)
        assert count == 500  # Every line has "Line"

    def test_count_case_insensitive(self, backend):
        """Test case-insensitive count."""
        count = backend.count_matches("line", case_sensitive=False)
        assert count == 500

    def test_count_whole_word(self, backend):
        """Test whole-word count."""
        count = backend.count_matches("content", case_sensitive=True, whole_word=True)
        assert count == 500

    def test_count_whole_word_case_insensitive(self, backend):
        """Test whole-word case-insensitive count."""
        count = backend.count_matches("CONTENT", case_sensitive=False, whole_word=True)
        assert count == 500

    def test_count_no_match(self, backend):
        """Test count with no matches."""
        count = backend.count_matches("ZZZZNOTFOUND")
        assert count == 0


class TestFindNext:
    """Test forward search."""

    def test_find_next_basic(self, backend):
        """Test finding next occurrence."""
        result = backend.find_next_in_file("Line 10:", 0, case_sensitive=True)
        assert result is not None

    def test_find_next_wrap_around(self, backend):
        """Test find next wraps around to beginning."""
        # Search from near the end for something at the start
        result = backend.find_next_in_file("Line 0:", backend._file_size - 10)
        assert result is not None
        assert result == 0  # Should find at start

    def test_find_next_case_insensitive(self, backend):
        """Test case-insensitive forward search."""
        result = backend.find_next_in_file("line 0:", 0, case_sensitive=False)
        assert result is not None

    def test_find_next_whole_word(self, backend):
        """Test whole-word forward search."""
        result = backend.find_next_in_file("content", 0, case_sensitive=True, whole_word=True)
        assert result is not None

    def test_find_next_whole_word_case_insensitive(self, backend):
        """Test whole-word case-insensitive forward search."""
        result = backend.find_next_in_file("CONTENT", 0, case_sensitive=False, whole_word=True)
        assert result is not None

    def test_find_next_no_match(self, backend):
        """Test find next returns None when no match."""
        result = backend.find_next_in_file("NOTFOUND999", 0)
        assert result is None

    def test_find_next_case_insensitive_wrap(self, backend):
        """Test case-insensitive search wraps around."""
        result = backend.find_next_in_file("line 0:", backend._file_size - 10, case_sensitive=False)
        assert result is not None

    def test_find_next_whole_word_wrap(self, backend):
        """Test whole-word search wraps around."""
        # Search from near the end
        result = backend.find_next_in_file("some", backend._file_size - 5, case_sensitive=True, whole_word=True)
        assert result is not None  # Should wrap and find earlier occurrences


class TestFindPrev:
    """Test backward search."""

    def test_find_prev_basic(self, backend):
        """Test finding previous occurrence."""
        result = backend.find_prev_in_file("Line", backend._file_size)
        assert result is not None

    def test_find_prev_case_sensitive(self, backend):
        """Test case-sensitive backward search."""
        result = backend.find_prev_in_file("Line 0:", backend._file_size, case_sensitive=True)
        assert result is not None
        assert result == 0

    def test_find_prev_case_insensitive(self, backend):
        """Test case-insensitive backward search."""
        result = backend.find_prev_in_file("line 0:", backend._file_size, case_sensitive=False)
        assert result is not None

    def test_find_prev_wrap_around(self, backend):
        """Test backward search wraps to end."""
        # Search backward from byte 5 for something that only appears later
        result = backend.find_prev_in_file("Line 499:", 5, case_sensitive=True)
        assert result is not None

    def test_find_prev_whole_word(self, backend):
        """Test whole-word backward search."""
        result = backend.find_prev_in_file("content", backend._file_size, case_sensitive=True, whole_word=True)
        assert result is not None

    def test_find_prev_whole_word_wrap(self, backend):
        """Test whole-word backward search wrap."""
        result = backend.find_prev_in_file("content", 5, case_sensitive=True, whole_word=True)
        assert result is not None

    def test_find_prev_case_insensitive_wrap(self, backend):
        """Test case-insensitive backward search wrap."""
        result = backend.find_prev_in_file("line 499:", 5, case_sensitive=False)
        assert result is not None

    def test_find_prev_no_match(self, backend):
        """Test find prev returns None when no match."""
        result = backend.find_prev_in_file("NOTFOUND999", backend._file_size)
        assert result is None


class TestReplaceAll:
    """Test bulk replace operations."""

    def test_replace_all_case_sensitive(self, backend):
        """Test case-sensitive replace all."""
        count = backend.replace_all("content", "REPLACED", case_sensitive=True)
        assert count == 500

    def test_replace_all_case_insensitive(self, backend):
        """Test case-insensitive replace all."""
        count = backend.replace_all("CONTENT", "replaced", case_sensitive=False)
        assert count == 500

    def test_replace_all_whole_word(self, backend):
        """Test whole-word replace all."""
        count = backend.replace_all("content", "REPLACED", case_sensitive=True, whole_word=True)
        assert count == 500

    def test_replace_all_no_match(self, backend):
        """Test replace all with no matches."""
        count = backend.replace_all("NOTFOUND999", "replacement")
        assert count == 0


class TestReplaceWindow:
    """Test window-based editing."""

    def test_replace_window_unchanged(self, backend):
        """Test replacing window with same content creates no patch."""
        text, ws, we = backend.get_window_text(0)
        backend.replace_window(ws, we, text)
        # No patches should be created for unchanged text
        assert len(backend._patches) == 0

    def test_replace_window_modified(self, backend):
        """Test replacing window with modified content creates a patch."""
        text, ws, we = backend.get_window_text(0)
        modified = text.replace("Line 0:", "MODIFIED:")
        backend.replace_window(ws, we, modified)
        patches = backend._to_list_patches()
        assert len(patches) > 0


class TestSaveTo:
    """Test saving with patches applied."""

    def test_save_with_replace_all(self, backend, tmp_path):
        """Test saving after replace all."""
        count = backend.replace_all("content", "REPLACED", case_sensitive=True)
        assert count == 500

        new_path = str(tmp_path / "saved.txt")
        backend.save_to(new_path)

        saved_text = open(new_path).read()
        assert "REPLACED" in saved_text
        assert saved_text.count("REPLACED") == 500

    def test_save_with_window_edit(self, backend, tmp_path):
        """Test saving after window-level edit."""
        text, ws, we = backend.get_window_text(0)
        modified = text.replace("Line 0:", "EDITED:")
        backend.replace_window(ws, we, modified)

        new_path = str(tmp_path / "edited.txt")
        backend.save_to(new_path)

        saved_text = open(new_path).read()
        assert "EDITED:" in saved_text

    def test_save_remaps_file(self, backend, tmp_path):
        """Test that save_to re-mmaps the new file."""
        backend.replace_all("content", "X", case_sensitive=True)
        new_path = str(tmp_path / "remapped.txt")
        backend.save_to(new_path)

        # After save, backend should point to new file
        assert backend.file_path == new_path
        # And patches should be cleared
        assert len(backend._patches) == 0


class TestCompactPatches:
    """Test the _CompactPatches data structure."""

    def test_len(self):
        """Test __len__."""
        patches = _CompactPatches(
            starts=array.array('Q', [0, 10]),
            ends=array.array('Q', [5, 15]),
            repl_bytes=b'X'
        )
        assert len(patches) == 2

    def test_iter(self):
        """Test __iter__."""
        patches = _CompactPatches(
            starts=array.array('Q', [0, 10]),
            ends=array.array('Q', [5, 15]),
            repl_bytes=b'X'
        )
        items = list(patches)
        assert items == [(0, 5, b'X'), (10, 15, b'X')]

    def test_clear(self):
        """Test clear."""
        patches = _CompactPatches(
            starts=array.array('Q', [0]),
            ends=array.array('Q', [5]),
            repl_bytes=b'X'
        )
        patches.clear()
        assert len(patches) == 0


class TestCloseBackend:
    """Test resource cleanup."""

    def test_close(self, tmp_path):
        """Test that close() cleans up resources."""
        path = tmp_path / "close_test.txt"
        path.write_text("test content\n")
        be = LargeFileBackend(str(path))
        be.close()
        # Should not raise on double close
        be.close()
