# TextEdit Performance Timings

## Timings

| Operation | small.txt | medium.txt | large.txt |
|---|---|---|---|
| File size | 6 KB (200 lines) | 329 KB (10,000 lines) | 252 MB (1,474,078 lines) |
| Open file | 29.3 ms | 18.6 ms | 137.8 ms [large-file mode] |
| Scroll (max) | 4.3 ms | 4.2 ms | 13.4 ms |
| Scroll (avg) | 2.9 ms | 3.6 ms | 8.8 ms |
| Count "while" | 0.1 ms | 2.2 ms | 120.1 ms |
| Replace "while"→"for" | 3.2 ms | 14.2 ms | 169.6 ms |
| Match count | 19 | 1,186 | 668,753 |
| Memory (physical) | 199 MB | 221 MB | 569 MB |

## Optimizations

- **Replace-all via Python string ops:** `replace_all()` extracts text with `toPlainText()`, performs replacement in Python using `str.replace()` or `re.subn()`, then sets the result back with a single `setPlainText()` call — avoiding 668K individual cursor edits on large files.

- **Match counting via Python string ops:** Uses `str.count()` for case-sensitive searches, `str.lower().count()` for case-insensitive, and `re.findall()` with `\b` word boundaries for whole-word — all on the raw Python string instead of a `QTextDocument.find()` loop.

- **Debounced match counting (150ms QTimer):** Each keystroke in the search field restarts a 150ms timer, so the count only fires once the user pauses typing.

- **Frame timer (FrameTimerWidget):** `src/frame_timer.py` measures real frame timings via an `eventFilter` on `QApplication`. Toggled with Ctrl+P. Displays last, average, and max frame times over the last 300 frames.

- **Benchmark script (benchmark.py):** Automated, repeatable timing of open, scroll, and replace-all operations across small/medium/large test files.

- **Chunked file loading via mmap (large-file mode):** Files >= 10 MB activate `LargeFileBackend` (`src/large_file_backend.py`), which uses `mmap` for OS-level paging and builds a line-offset index. Only a 10,000-line window around the viewport is loaded into `QPlainTextEdit`. A virtual scrollbar maps to the full file line range with 80ms debounced window reloading. Find/replace scans the mmap directly: `count_matches()` uses `mmap.find()` or `re.finditer()`, `replace_all()` builds byte-range patches without modifying the mmap, and `save_to()` streams unchanged + patched regions to disk. Split-view sync is disabled for large files. Undo/redo works within the loaded window but is cleared on window reload.

- **Memory-efficient data structures (large-file mode):** Line offsets use `array.array('Q')` (8 bytes/entry) instead of Python `list[int]` (approx 28 bytes/entry), saving approx 29 MB for 1.47M lines. Replace-all patches use a compact `_CompactPatches` dataclass with two `array.array('Q')` for start/end positions and a single shared replacement bytes reference, instead of 668K 3-tuples (approx 43 MB savings). `count_matches()` uses `re.finditer()` iterator counting instead of `re.findall()` list materialization, avoiding approx 20-40 MB transient allocation.

- **Benchmark avoids inflating RSS:** The benchmark skips `f.read()` for large files (which would create an approx 500 MB Python string), instead reading line count from the editor backend.

- **Chunked reverse search:** `find_prev_in_file()` uses a reverse-chunked 1 MB scan with `re.finditer()` instead of slicing the entire mmap prefix (up to 252 MB) for regex paths.

- **C-level regex scanning for count and replace (large-file mode):** `count_matches()` and `replace_all()` case-sensitive paths now use `re.compile(re.escape(search_bytes)).finditer(mmap)` instead of a Python `while` loop calling `mmap.find()` 668K times. The compiled regex engine iterates entirely in C, avoiding per-call Python interpreter overhead (function call, integer boxing, comparison). Count improved from 168 ms to 120 ms (29% faster), replace from 214 ms to 170 ms (21% faster).

- **Chunked forward search for find-next:** `find_next_in_file()` regex paths (whole-word and case-insensitive) now use `_find_forward_chunked()` with 1 MB chunks and overlap instead of `self._mm[from_byte:]` which would copy up to 252 MB of data. This prevents transient memory spikes during interactive find operations.

## Notes

For small/medium files, the dominant cost is Qt's `setPlainText()`, which creates QTextBlock objects in C++. For large files, the mmap backend bypasses this entirely — the bottleneck shifts to building the line-offset index (~135 ms) and regex scanning for find/replace (120-170 ms). Memory stayed at 569 MB through compact data structures and avoiding unnecessary Python allocations. Scrolling remains fast across all file sizes.
