"""Backend for memory-efficient large file handling via mmap."""

import array
import bisect
import dataclasses
import mmap
import os
import re
import tempfile
import threading


LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10 MB
WINDOW_LINES = 10_000
_PARTIAL_INDEX_LINES = 20_000  # lines indexed synchronously on open


@dataclasses.dataclass
class _CompactPatches:
    """Memory-efficient patch storage for uniform replacements."""
    starts: array.array  # 'Q' (unsigned 64-bit)
    ends: array.array    # 'Q'
    repl_bytes: bytes

    def __len__(self):
        return len(self.starts)

    def __iter__(self):
        for i in range(len(self.starts)):
            yield self.starts[i], self.ends[i], self.repl_bytes

    def clear(self):
        self.starts = array.array('Q')
        self.ends = array.array('Q')


class LargeFileBackend:
    """Manages a large file via mmap with windowed access and edit patches."""

    def __init__(self, file_path: str, on_index_ready=None):
        self._file_path = file_path
        self._file_size = os.path.getsize(file_path)
        self._fd = open(file_path, 'rb')
        self._mm = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_READ)
        self._line_offsets: array.array = array.array('Q')
        self._patches: list[tuple[int, int, bytes]] | _CompactPatches = []  # (start, end, replacement)
        self._mmap_lock = threading.Lock()
        self._index_complete = False
        self._index_thread: threading.Thread | None = None
        self._on_index_ready = on_index_ready
        self._build_partial_index(_PARTIAL_INDEX_LINES)
        self._start_full_index()

    def _build_partial_index(self, max_lines: int):
        """Index the first max_lines lines synchronously (fast, <5ms)."""
        offsets = [0]
        mm = self._mm
        pos = 0
        count = 0
        while count < max_lines:
            idx = mm.find(b'\n', pos)
            if idx == -1:
                # File has fewer lines than max_lines — index is complete
                self._index_complete = True
                break
            offsets.append(idx + 1)
            pos = idx + 1
            count += 1
        self._line_offsets = array.array('Q', offsets)
        if self._index_complete and self._on_index_ready:
            self._on_index_ready()

    def _start_full_index(self):
        """Launch a daemon thread to finish indexing beyond the partial index."""
        if self._index_complete:
            return
        self._index_thread = threading.Thread(
            target=self._build_full_index, daemon=True)
        self._index_thread.start()

    def _build_full_index(self):
        """Build the complete line index on a background thread."""
        mm = self._mm
        # Continue from where partial index stopped
        if len(self._line_offsets) > 0:
            pos = self._line_offsets[-1]
            # Find the next newline from where we left off
            idx = mm.find(b'\n', pos)
            if idx == -1:
                with self._mmap_lock:
                    self._index_complete = True
                if self._on_index_ready:
                    self._on_index_ready()
                return
            pos = idx + 1
        else:
            pos = 0

        new_offsets = []
        while True:
            idx = mm.find(b'\n', pos)
            if idx == -1:
                break
            new_offsets.append(idx + 1)
            pos = idx + 1

        with self._mmap_lock:
            self._line_offsets.extend(array.array('Q', new_offsets))
            self._index_complete = True
        if self._on_index_ready:
            self._on_index_ready()

    @property
    def index_complete(self) -> bool:
        return self._index_complete

    @property
    def total_lines(self) -> int:
        return len(self._line_offsets)

    @property
    def file_path(self) -> str:
        return self._file_path

    def get_window_text(self, center_line: int) -> tuple[str, int, int]:
        """Return (text, win_start, win_end) for ~WINDOW_LINES centered on center_line."""
        half = WINDOW_LINES // 2
        win_start = max(0, center_line - half)
        win_end = min(self.total_lines, win_start + WINDOW_LINES)
        # Adjust start if we hit the end
        if win_end - win_start < WINDOW_LINES:
            win_start = max(0, win_end - WINDOW_LINES)

        byte_start = self._line_offsets[win_start]
        if win_end >= self.total_lines:
            byte_end = self._file_size
        else:
            byte_end = self._line_offsets[win_end]

        raw = self._mm[byte_start:byte_end]
        text = raw.decode('utf-8', errors='replace')
        # Strip trailing newline to match Qt's block model
        if text.endswith('\n'):
            text = text[:-1]
        return text, win_start, win_end

    def byte_offset_to_line(self, byte_offset: int) -> int:
        """Convert a byte offset to a line number using bisect."""
        idx = bisect.bisect_right(self._line_offsets, byte_offset) - 1
        return max(0, idx)

    def line_to_byte_offset(self, line: int) -> int:
        """Convert a line number to the byte offset of that line's start."""
        if line < 0:
            return 0
        if line >= len(self._line_offsets):
            return self._file_size
        return self._line_offsets[line]

    def count_matches(self, search: str, case_sensitive: bool = True,
                      whole_word: bool = False) -> int:
        """Count all matches in the file by scanning the mmap."""
        if whole_word:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = rb'\b' + re.escape(search.encode('utf-8')) + rb'\b'
            return sum(1 for _ in re.finditer(pattern, self._mm, flags))

        search_bytes = search.encode('utf-8')
        if not case_sensitive:
            # For case-insensitive, use regex
            pattern = re.escape(search_bytes)
            return sum(1 for _ in re.finditer(pattern, self._mm, re.IGNORECASE))

        pattern = re.compile(re.escape(search_bytes))
        return sum(1 for _ in pattern.finditer(self._mm))

    def count_matches_async(self, search: str, case_sensitive: bool,
                            whole_word: bool, cancel_event: threading.Event) -> int:
        """Count matches with periodic cancellation checks (for worker thread)."""
        search_bytes = search.encode('utf-8')
        if whole_word:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = rb'\b' + re.escape(search_bytes) + rb'\b'
        elif not case_sensitive:
            pattern = re.escape(search_bytes)
            flags = re.IGNORECASE
        else:
            pattern = re.compile(re.escape(search_bytes))
            flags = 0

        count = 0
        with self._mmap_lock:
            mm = self._mm
        for _ in (re.finditer(pattern, mm, flags) if not isinstance(pattern, re.Pattern)
                  else pattern.finditer(mm)):
            count += 1
            if count % 10_000 == 0 and cancel_event.is_set():
                return 0
        return count

    def find_next_in_file(self, search: str, from_byte: int,
                          case_sensitive: bool = True,
                          whole_word: bool = False) -> int | None:
        """Find the next match starting from from_byte. Returns byte offset or None."""
        search_bytes = search.encode('utf-8')

        if whole_word:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = rb'\b' + re.escape(search_bytes) + rb'\b'
            result = self._find_forward_chunked(pattern, from_byte, flags)
            if result is not None:
                return result
            # Wrap around: search from start to from_byte
            result = self._find_forward_chunked(pattern, 0, flags, end_byte=from_byte)
            return result

        if case_sensitive:
            idx = self._mm.find(search_bytes, from_byte)
            if idx != -1:
                return idx
            # Wrap around
            idx = self._mm.find(search_bytes, 0, from_byte)
            return idx if idx != -1 else None
        else:
            pattern = re.escape(search_bytes)
            flags = re.IGNORECASE
            result = self._find_forward_chunked(pattern, from_byte, flags)
            if result is not None:
                return result
            # Wrap around
            result = self._find_forward_chunked(pattern, 0, flags, end_byte=from_byte)
            return result

    def _find_forward_chunked(self, pattern, from_byte: int, flags: int,
                                 end_byte: int | None = None) -> int | None:
        """Find the first regex match from from_byte using chunked forward search."""
        CHUNK = 1 * 1024 * 1024  # 1 MB
        if end_byte is None:
            end_byte = self._file_size
        # Need overlap to avoid missing matches split across chunk boundaries
        overlap = max(256, len(pattern) if isinstance(pattern, bytes) else 256)
        pos = from_byte
        while pos < end_byte:
            chunk_end = min(pos + CHUNK, end_byte)
            # Extend chunk by overlap to catch boundary matches (but not beyond file)
            read_end = min(chunk_end + overlap, self._file_size)
            m = re.search(pattern, self._mm[pos:read_end], flags)
            if m:
                match_pos = pos + m.start()
                if match_pos < end_byte:
                    return match_pos
                return None
            pos = chunk_end
        return None

    def _rfind_regex(self, pattern, end_byte: int, flags: int) -> int | None:
        """Find the last regex match before end_byte using reverse-chunked search."""
        CHUNK = 1 * 1024 * 1024  # 1 MB
        chunk_end = end_byte
        while chunk_end > 0:
            chunk_start = max(0, chunk_end - CHUNK)
            # Read chunk from mmap without slicing: use mmap[start:end]
            # but limit chunk size to avoid huge copies
            last_match = None
            for m in re.finditer(pattern, self._mm[chunk_start:chunk_end], flags):
                last_match = chunk_start + m.start()
            if last_match is not None:
                return last_match
            chunk_end = chunk_start
        return None

    def find_prev_in_file(self, search: str, from_byte: int,
                          case_sensitive: bool = True,
                          whole_word: bool = False) -> int | None:
        """Find the previous match before from_byte. Returns byte offset or None."""
        search_bytes = search.encode('utf-8')

        if whole_word:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = rb'\b' + re.escape(search_bytes) + rb'\b'
            result = self._rfind_regex(pattern, from_byte, flags)
            if result is not None:
                return result
            # Wrap around: search from from_byte to end
            result = self._rfind_regex(pattern, self._file_size, flags)
            if result is not None and result >= from_byte:
                return result
            return None

        if case_sensitive:
            idx = self._mm.rfind(search_bytes, 0, from_byte)
            if idx != -1:
                return idx
            # Wrap around
            idx = self._mm.rfind(search_bytes, from_byte)
            return idx if idx != -1 else None
        else:
            pattern = re.escape(search_bytes)
            result = self._rfind_regex(pattern, from_byte, re.IGNORECASE)
            if result is not None:
                return result
            # Wrap around
            result = self._rfind_regex(pattern, self._file_size, re.IGNORECASE)
            if result is not None and result >= from_byte:
                return result
            return None

    def replace_all(self, search: str, replacement: str,
                    case_sensitive: bool = True,
                    whole_word: bool = False) -> int:
        """Build compact patch arrays for replacing all occurrences. Returns count."""
        search_bytes = search.encode('utf-8')
        repl_bytes = replacement.encode('utf-8')
        starts = []
        ends = []

        if whole_word:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = rb'\b' + re.escape(search_bytes) + rb'\b'
            for m in re.finditer(pattern, self._mm, flags):
                starts.append(m.start())
                ends.append(m.end())
        elif case_sensitive:
            pattern = re.compile(re.escape(search_bytes))
            for m in pattern.finditer(self._mm):
                starts.append(m.start())
                ends.append(m.end())
        else:
            pattern = re.escape(search_bytes)
            for m in re.finditer(pattern, self._mm, re.IGNORECASE):
                starts.append(m.start())
                ends.append(m.end())

        self._patches = _CompactPatches(
            starts=array.array('Q', starts),
            ends=array.array('Q', ends),
            repl_bytes=repl_bytes,
        )
        return len(self._patches)

    def replace_all_async(self, search: str, replacement: str,
                          case_sensitive: bool, whole_word: bool,
                          cancel_event: threading.Event) -> int:
        """Build patches with periodic cancellation checks (for worker thread)."""
        search_bytes = search.encode('utf-8')
        repl_bytes = replacement.encode('utf-8')
        starts = []
        ends = []

        if whole_word:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = rb'\b' + re.escape(search_bytes) + rb'\b'
        elif not case_sensitive:
            pattern = re.escape(search_bytes)
            flags = re.IGNORECASE
        else:
            pattern = re.compile(re.escape(search_bytes))
            flags = 0

        with self._mmap_lock:
            mm = self._mm

        iterator = (re.finditer(pattern, mm, flags) if not isinstance(pattern, re.Pattern)
                    else pattern.finditer(mm))
        count = 0
        for m in iterator:
            starts.append(m.start())
            ends.append(m.end())
            count += 1
            if count % 10_000 == 0 and cancel_event.is_set():
                return 0

        with self._mmap_lock:
            self._patches = _CompactPatches(
                starts=array.array('Q', starts),
                ends=array.array('Q', ends),
                repl_bytes=repl_bytes,
            )
        return len(self._patches)

    def _to_list_patches(self) -> list[tuple[int, int, bytes]]:
        """Convert current patches to a list of tuples."""
        if isinstance(self._patches, _CompactPatches):
            return list(self._patches)
        return self._patches

    def replace_window(self, win_start: int, win_end: int, edited_text: str):
        """Store the current window's edited text as a consolidated patch."""
        byte_start = self._line_offsets[win_start]
        if win_end >= self.total_lines:
            byte_end = self._file_size
        else:
            byte_end = self._line_offsets[win_end]

        original = self._mm[byte_start:byte_end]
        edited_bytes = edited_text.encode('utf-8')
        # Add back trailing newline if original had one
        if original.endswith(b'\n') and not edited_bytes.endswith(b'\n'):
            edited_bytes += b'\n'

        if edited_bytes != original:
            # Convert to list patches for mixed editing
            patches = self._to_list_patches()
            # Remove any existing patches that overlap with this window
            patches = [
                (s, e, r) for s, e, r in patches
                if e <= byte_start or s >= byte_end
            ]
            patches.append((byte_start, byte_end, edited_bytes))
            patches.sort(key=lambda p: p[0])
            self._patches = patches

    def save_to(self, path: str):
        """Write the file with all patches applied."""
        if isinstance(self._patches, _CompactPatches):
            # Already sorted by construction
            patches = self._patches
        else:
            patches = sorted(self._patches, key=lambda p: p[0])

        # Write to a temp file first, then rename
        dir_name = os.path.dirname(path) or '.'
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
        try:
            with os.fdopen(fd, 'wb') as out:
                pos = 0
                if isinstance(patches, _CompactPatches):
                    repl = patches.repl_bytes
                    for i in range(len(patches.starts)):
                        s = patches.starts[i]
                        e = patches.ends[i]
                        if s > pos:
                            out.write(self._mm[pos:s])
                        out.write(repl)
                        pos = e
                else:
                    for start, end, replacement in patches:
                        if start > pos:
                            out.write(self._mm[pos:start])
                        out.write(replacement)
                        pos = end
                # Write remaining data
                if pos < self._file_size:
                    out.write(self._mm[pos:self._file_size])
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        # Re-mmap the new file
        self._patches.clear()
        self._mm.close()
        self._fd.close()
        self._file_path = path
        self._file_size = os.path.getsize(path)
        self._fd = open(path, 'rb')
        self._mm = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_READ)
        self._index_complete = False
        self._build_partial_index(_PARTIAL_INDEX_LINES)
        self._start_full_index()

    def close(self):
        """Clean up resources."""
        # Cancel and join background index thread
        if self._index_thread is not None and self._index_thread.is_alive():
            self._index_thread.join(timeout=2.0)
        try:
            self._mm.close()
        except Exception:
            pass
        try:
            self._fd.close()
        except Exception:
            pass
