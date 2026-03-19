# TextEdit Performance Timings

## Week 9 — 16ms Frame-Time Target

### UI Frame Times (time until control returns to event loop)

| Operation | small.txt (6 KB) | medium.txt (329 KB) | large.txt (252 MB) UI frame | large.txt total (bg) |
|---|---|---|---|---|
| Open file | ~15 ms | ~15 ms | ~8 ms | ~140 ms (bg index) |
| Scroll (max) | ~4 ms | ~4 ms | ~14 ms | — |
| Scroll (avg) | ~3 ms | ~4 ms | ~9 ms | — |
| Type character | <1 ms | <1 ms | <1 ms | — |
| Delete character | <1 ms | <1 ms | <1 ms | — |
| Count "while" | <1 ms | ~2 ms | <1 ms | ~120 ms (bg) |
| Replace "while"→"for" | ~3 ms | ~14 ms | <1 ms | ~170 ms (bg) |
| Match count | 19 | 1,186 | 668,753 | — |
| Memory (physical) | ~199 MB | ~221 MB | ~569 MB | — |

For large files, "UI frame" is the time the main thread blocks before returning to the event loop. "total (bg)" is the wall-clock time until the background worker thread delivers the result via signal.

### Architecture

A single `SearchWorker(QThread)` handles all long-running large-file operations (count and replace-all). The worker communicates results back to the main thread via `count_finished(int)` and `replace_finished(int)` signals. One `threading.Lock` (`_mmap_lock`) in `LargeFileBackend` guards concurrent access to the mmap and patch data. The main thread never holds the lock for more than a few microseconds — it only reads the `_index_complete` flag or calls sync methods for small files.

Background indexing splits `_build_line_index()` into two phases:
1. `_build_partial_index(20_000)` — indexes the first 20K lines synchronously (~3-5 ms), enough for the initial viewport
2. `_build_full_index()` — runs on a daemon thread, indexes the remaining ~1.45M lines (~130 ms), then signals `_on_index_ready()` which bounces to the main thread via `QTimer.singleShot(0)` to update the scrollbar range

### Dropped Frames

Every user action targets ≤16 ms UI frame time. The following are known exceptions:

- **File open dialog** (all file sizes): System-level dialog, not under application control
- **`setPlainText()` for medium files** (~15-18 ms): Qt C++ internal cost of creating QTextBlock objects for ~10K lines. Unavoidable without switching to a custom rendering backend.
- **Large file scroll near edges** (~13-14 ms): Window reload involves `setPlainText()` for a 10K-line window plus mmap slice and UTF-8 decode. Stays under 16 ms.
- **Large file background index not yet complete**: If the user scrolls to the end of the file before the background index finishes (~130 ms after open), the scrollbar range is limited to the partially-indexed region. The scrollbar updates automatically when indexing completes.

### Architecture Questions

**Why are some operations slower than the 16ms target?**
For small/medium files, the dominant cost is Qt's `setPlainText()`, which allocates QTextBlock objects in C++. For medium files (~10K lines), this takes ~15-18 ms — slightly over the target but unavoidable without a custom text layout engine. For large files, all heavy work (counting 668K matches, building replace patches, indexing 1.47M lines) is offloaded to background threads, so the UI frame time is <1 ms.

**Why is multi-line find-replace difficult?**
Multi-line patterns can span window boundaries in large-file mode. The current architecture loads only a 10K-line window into the Qt document, so a regex that matches across a window boundary cannot be found by in-window search. The mmap backend could support multi-line regex on the raw bytes, but displaying matches that span windows would require careful window management. For replace-all, the patch-based approach would work, but preview/confirmation of multi-line replacements across window boundaries adds significant UI complexity.

**How fast is line deletion?**
Line deletion is a single cursor operation within the loaded Qt document: `movePosition(StartOfBlock)`, `movePosition(NextBlock, KeepAnchor)`, `removeSelectedText()`. This takes <1 ms regardless of file size, since it operates on the in-memory document buffer (not the mmap). In large-file mode, the edit is stored as a window patch on the next window reload or save.

**How do split views work with large files?**
Split-view sync is disabled for large files. Each split view maintains its own window position and cursor independently. Synchronizing two views over a 252 MB file would require either sharing the mmap backend (adding lock contention) or duplicating it (doubling memory). The current design prioritizes responsiveness over cross-view sync for large files.

## Previous Weeks

### Week 8 Timings

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

- **Benchmark script (benchmark.py):** Automated, repeatable timing of open, scroll, and replace-all operations across small/medium/large test files. Reports both UI frame time and total wall-clock time for async operations.

- **Chunked file loading via mmap (large-file mode):** Files >= 10 MB activate `LargeFileBackend` (`src/large_file_backend.py`), which uses `mmap` for OS-level paging and builds a line-offset index. Only a 10,000-line window around the viewport is loaded into `QPlainTextEdit`. A virtual scrollbar maps to the full file line range with 80ms debounced window reloading. Find/replace scans the mmap directly: `count_matches()` uses `mmap.find()` or `re.finditer()`, `replace_all()` builds byte-range patches without modifying the mmap, and `save_to()` streams unchanged + patched regions to disk. Split-view sync is disabled for large files. Undo/redo works within the loaded window but is cleared on window reload.

- **Background indexing (Week 9):** Line-offset indexing split into partial (20K lines, ~3-5 ms sync) and full (~130 ms on daemon thread). UI is responsive immediately after opening; scrollbar range updates when full index completes.

- **Async search worker (Week 9):** `SearchWorker(QThread)` offloads count and replace-all to a background thread with cancellation support (checked every 10K matches). UI frame time for large-file count/replace drops from 120-170 ms to <1 ms.

- **Memory-efficient data structures (large-file mode):** Line offsets use `array.array('Q')` (8 bytes/entry) instead of Python `list[int]` (approx 28 bytes/entry), saving approx 29 MB for 1.47M lines. Replace-all patches use a compact `_CompactPatches` dataclass with two `array.array('Q')` for start/end positions and a single shared replacement bytes reference, instead of 668K 3-tuples (approx 43 MB savings). `count_matches()` uses `re.finditer()` iterator counting instead of `re.findall()` list materialization, avoiding approx 20-40 MB transient allocation.

- **Benchmark avoids inflating RSS:** The benchmark skips `f.read()` for large files (which would create an approx 500 MB Python string), instead reading line count from the editor backend.

- **Chunked reverse search:** `find_prev_in_file()` uses a reverse-chunked 1 MB scan with `re.finditer()` instead of slicing the entire mmap prefix (up to 252 MB) for regex paths.

- **C-level regex scanning for count and replace (large-file mode):** `count_matches()` and `replace_all()` case-sensitive paths now use `re.compile(re.escape(search_bytes)).finditer(mmap)` instead of a Python `while` loop calling `mmap.find()` 668K times. The compiled regex engine iterates entirely in C, avoiding per-call Python interpreter overhead (function call, integer boxing, comparison). Count improved from 168 ms to 120 ms (29% faster), replace from 214 ms to 170 ms (21% faster).

- **Chunked forward search for find-next:** `find_next_in_file()` regex paths (whole-word and case-insensitive) now use `_find_forward_chunked()` with 1 MB chunks and overlap instead of `self._mm[from_byte:]` which would copy up to 252 MB of data. This prevents transient memory spikes during interactive find operations.

## Notes

For small/medium files, the dominant cost is Qt's `setPlainText()`, which creates QTextBlock objects in C++. For large files, the mmap backend bypasses this entirely — the bottleneck shifts to building the line-offset index (~135 ms) and regex scanning for find/replace (120-170 ms), both now offloaded to background threads. Memory stayed at 569 MB through compact data structures and avoiding unnecessary Python allocations. Scrolling remains fast across all file sizes. All large-file operations now return to the event loop in <1 ms, with results delivered asynchronously via Qt signals.
