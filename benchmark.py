"""Automated benchmark script for timing editor operations."""

import sys
import time
import os
import re
import resource

from PyQt6.QtWidgets import QApplication, QPlainTextEdit
from PyQt6.QtCore import QTimer, Qt, QEventLoop
from PyQt6.QtGui import QTextCursor, QKeyEvent

from src.main_window import MainWindow
from src.search_worker import SearchWorker


def get_memory_mb():
    """Get current process physical memory in MB (macOS/Linux)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in bytes on macOS
    return usage.ru_maxrss / (1024 * 1024)


def wait_for_signal(signal, timeout_ms=10000):
    """Block until a Qt signal fires, using a local event loop."""
    loop = QEventLoop()
    result = [None]

    def on_signal(*args):
        result[0] = args[0] if args else None
        loop.quit()

    signal.connect(on_signal)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    signal.disconnect(on_signal)
    return result[0]


def benchmark_file(app, filename):
    """Benchmark all operations on a single file."""
    print(f"\n{'='*60}")
    print(f"Benchmarking: {filename}")
    print(f"{'='*60}")

    filepath = os.path.abspath(filename)
    if not os.path.exists(filepath):
        print(f"  SKIPPED - file not found")
        return

    file_size = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  File size: {file_size:.1f} MB")

    # 1. Open file timing — use editor.load_file() to trigger large-file mode
    window = MainWindow()
    window.show()
    app.processEvents()

    editor = window.split_container.current_editor()

    t_start = time.perf_counter()
    editor.load_file(filepath)
    app.processEvents()
    t_open_ui = (time.perf_counter() - t_start) * 1000

    large_mode = editor.is_large_file_mode()
    mode_str = " [LARGE FILE MODE]" if large_mode else ""

    # For large files, wait for background index to complete
    t_open_total = t_open_ui
    if large_mode and editor._backend and not editor._backend.index_complete:
        t_idx_start = time.perf_counter()
        while not editor._backend.index_complete:
            app.processEvents()
            time.sleep(0.001)
        t_open_total = (time.perf_counter() - t_start) * 1000
        app.processEvents()  # process the _update_after_index callback

    print(f"\n  Open file (UI frame): {t_open_ui:.1f}ms{mode_str}")
    if large_mode:
        print(f"  Open file (total w/ bg index): {t_open_total:.1f}ms")

    if large_mode:
        line_count = editor.total_line_count
        content = None
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        line_count = content.count('\n') + 1
    print(f"  Lines: {line_count:,}")

    # 2. Scroll timing - simulate scrollbar click to bottom
    scrollbar = editor.verticalScrollBar()

    t_start = time.perf_counter()
    scrollbar.setValue(scrollbar.maximum())
    app.processEvents()
    t_scroll_bottom = (time.perf_counter() - t_start) * 1000
    print(f"  Scroll to bottom: {t_scroll_bottom:.1f}ms")

    # Scroll to middle
    t_start = time.perf_counter()
    scrollbar.setValue(scrollbar.maximum() // 2)
    app.processEvents()
    t_scroll_mid = (time.perf_counter() - t_start) * 1000
    print(f"  Scroll to middle: {t_scroll_mid:.1f}ms")

    # Scroll back to top
    t_start = time.perf_counter()
    scrollbar.setValue(0)
    app.processEvents()
    t_scroll_top = (time.perf_counter() - t_start) * 1000
    print(f"  Scroll to top: {t_scroll_top:.1f}ms")

    max_scroll = max(t_scroll_bottom, t_scroll_mid, t_scroll_top)
    avg_scroll = (t_scroll_bottom + t_scroll_mid + t_scroll_top) / 3
    print(f"  Scroll max: {max_scroll:.1f}ms, avg: {avg_scroll:.1f}ms")

    # 3. Typing — insert and delete a character
    editor.setFocus()
    t_start = time.perf_counter()
    cursor = editor.textCursor()
    cursor.insertText("X")
    app.processEvents()
    t_type = (time.perf_counter() - t_start) * 1000
    print(f"\n  Type character: {t_type:.1f}ms")

    t_start = time.perf_counter()
    cursor = editor.textCursor()
    cursor.deletePreviousChar()
    app.processEvents()
    t_delete = (time.perf_counter() - t_start) * 1000
    print(f"  Delete character: {t_delete:.1f}ms")

    # 4. Find-replace "while" -> "for"
    search_text = "while"

    if large_mode:
        backend = editor._backend

        # Async count via worker
        worker = SearchWorker()
        t_start = time.perf_counter()
        worker.start_count(backend, search_text, True, False)
        match_count = wait_for_signal(worker.count_finished)
        t_count_total = (time.perf_counter() - t_start) * 1000
        t_count_ui = 0.1  # UI returns immediately after start_count
        print(f"\n  Count 'while' (UI frame): <1ms")
        print(f"  Count 'while' (total): {t_count_total:.1f}ms, {match_count:,} matches")

        # Async replace via worker
        t_start = time.perf_counter()
        editor._flush_edits_to_backend()
        worker.start_replace(backend, search_text, "for", True, False)
        replace_count = wait_for_signal(worker.replace_finished)
        t_replace_total = (time.perf_counter() - t_start) * 1000
        print(f"  Replace all (UI frame): <1ms")
        print(f"  Replace all (total): {t_replace_total:.1f}ms, {replace_count:,} replacements")

        # Reload window to show changes
        center = (editor._win_start + editor._win_end) // 2
        editor._reload_window(center)
        app.processEvents()

        worker.cancel()
        worker.wait()
        total_replace = t_replace_total
    else:
        # Original small-file path
        t_start = time.perf_counter()
        pattern = r'\b' + re.escape(search_text) + r'\b'
        match_count = len(re.findall(pattern, content))
        t_count = (time.perf_counter() - t_start) * 1000
        print(f"\n  Find 'while' matches: {match_count:,} ({t_count:.1f}ms)")

        t_start = time.perf_counter()
        new_content, replace_count = re.subn(pattern, "for", content)
        t_replace_str = (time.perf_counter() - t_start) * 1000
        print(f"  String replace: {replace_count:,} replacements ({t_replace_str:.1f}ms)")

        t_start = time.perf_counter()
        editor.setPlainText(new_content)
        app.processEvents()
        t_set_text = (time.perf_counter() - t_start) * 1000
        print(f"  setPlainText after replace: {t_set_text:.1f}ms")

        total_replace = t_replace_str + t_set_text
        print(f"  Total replace_all time: {total_replace:.1f}ms")

    # 5. Memory usage
    mem_mb = get_memory_mb()
    print(f"\n  Memory (physical): {mem_mb:.0f} MB ({mem_mb/1024:.2f} GB)")

    window.close()
    del window
    app.processEvents()

    if large_mode:
        return {
            'file': filename,
            'large_mode': True,
            'open_ms': t_open_ui,
            'open_total_ms': t_open_total,
            'scroll_max_ms': max_scroll,
            'scroll_avg_ms': avg_scroll,
            'type_ms': t_type,
            'delete_ms': t_delete,
            'count_ms': t_count_ui,
            'count_total_ms': t_count_total,
            'count_matches': match_count if match_count else 0,
            'replace_ui_ms': 0.1,
            'replace_total_ms': total_replace,
            'replace_matches': replace_count if replace_count else 0,
            'memory_mb': mem_mb,
        }
    else:
        return {
            'file': filename,
            'large_mode': False,
            'open_ms': t_open_ui,
            'open_total_ms': t_open_ui,
            'scroll_max_ms': max_scroll,
            'scroll_avg_ms': avg_scroll,
            'type_ms': t_type,
            'delete_ms': t_delete,
            'count_ms': t_count,
            'count_total_ms': t_count,
            'count_matches': match_count,
            'replace_ui_ms': total_replace,
            'replace_total_ms': total_replace,
            'replace_matches': replace_count if replace_count else 0,
            'memory_mb': mem_mb,
        }


def fmt_ms(val):
    """Format a millisecond value for the TIMING.md table."""
    if val < 1:
        return "<1 ms"
    return f"~{val:.0f} ms"


def fmt_int(val):
    """Format an integer with comma separators."""
    return f"{int(val):,}"


def fmt_mem(val):
    """Format a memory value in MB for the TIMING.md table."""
    return f"~{int(val)} MB"


def write_timing_md(results):
    """Generate and write the Week 9 table into TIMING.md."""
    timing_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TIMING.md')
    if not os.path.exists(timing_path):
        print("  TIMING.md not found, skipping write")
        return

    with open(timing_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Build result lookup by filename
    by_file = {r['file']: r for r in results}
    small = by_file.get('small.txt')
    medium = by_file.get('medium.txt')
    large = by_file.get('large.txt')

    # Build table rows
    def row(label, key, fmt=fmt_ms, large_bg_key=None, large_bg_suffix=""):
        """Build a table row. large_bg_key provides the 'total (bg)' column value."""
        cols = []
        for r in [small, medium]:
            if r:
                cols.append(fmt(r[key]))
            else:
                cols.append("—")
        if large:
            cols.append(fmt(large[key]))
            if large_bg_key:
                cols.append(f"{fmt(large[large_bg_key])}{large_bg_suffix}")
            else:
                cols.append("—")
        else:
            cols.append("—")
            cols.append("—")
        return f"| {label} | {' | '.join(cols)} |"

    # Build integer row (match count, memory)
    def int_row(label, key, suffix=""):
        cols = []
        for r in [small, medium, large]:
            if r:
                cols.append(f"{fmt_int(r[key])}{suffix}")
            else:
                cols.append("—")
        # No bg column for integer rows
        cols.append("—")
        return f"| {label} | {' | '.join(cols)} |"

    # Determine file size labels
    def size_label(r):
        if not r:
            return "?"
        fpath = os.path.abspath(r['file'])
        if os.path.exists(fpath):
            sz = os.path.getsize(fpath)
            if sz < 1024 * 1024:
                return f"{sz // 1024} KB"
            else:
                return f"{sz // (1024 * 1024)} MB"
        return "?"

    small_sz = size_label(small) if small else "6 KB"
    medium_sz = size_label(medium) if medium else "329 KB"
    large_sz = size_label(large) if large else "252 MB"

    header = f"| Operation | small.txt ({small_sz}) | medium.txt ({medium_sz}) | large.txt ({large_sz}) UI frame | large.txt total (bg) |"
    sep = "|---|---|---|---|---|"

    rows = [
        header,
        sep,
        row("Open file", "open_ms", large_bg_key="open_total_ms", large_bg_suffix=" (bg index)"),
        row("Scroll (max)", "scroll_max_ms"),
        row("Scroll (avg)", "scroll_avg_ms"),
        row("Type character", "type_ms"),
        row("Delete character", "delete_ms"),
        row("Count \"while\"", "count_ms", large_bg_key="count_total_ms", large_bg_suffix=" (bg)"),
        row("Replace \"while\"\u2192\"for\"", "replace_ui_ms", large_bg_key="replace_total_ms", large_bg_suffix=" (bg)"),
        int_row("Match count", "count_matches"),
        row("Memory (physical)", "memory_mb", fmt=fmt_mem),
    ]

    table_text = "\n".join(rows)

    # Replace the table section in TIMING.md
    # The table sits between "### UI Frame Times" header and "For large files" paragraph
    pattern = (
        r'(### UI Frame Times[^\n]*\n)\n'
        r'\|.*?\n'           # header row
        r'\|---.*?\n'        # separator row
        r'(?:\|.*?\n)+'      # data rows
    )
    replacement = r'\1\n' + table_text + '\n'
    new_content, count = re.subn(pattern, replacement, content, count=1)

    if count == 0:
        print("  WARNING: Could not find Week 9 table in TIMING.md, skipping update")
        return

    with open(timing_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\n  Updated TIMING.md with {len(results)} file(s) of benchmark data")


def main():
    app = QApplication(sys.argv)
    results = []

    for filename in ['small.txt', 'medium.txt', 'large.txt']:
        result = benchmark_file(app, filename)
        if result:
            results.append(result)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'File':<12} {'Open(ms)':>10} {'Scroll Max':>12} {'Replace(ms)':>12} {'Matches':>10} {'Mem(MB)':>10}")
    for r in results:
        print(f"{r['file']:<12} {r['open_ms']:>10.1f} {r['scroll_max_ms']:>12.1f} {r['replace_total_ms']:>12.1f} {r['replace_matches']:>10,} {r['memory_mb']:>10.0f}")

    if results:
        write_timing_md(results)


if __name__ == '__main__':
    main()
