"""Automated benchmark script for timing editor operations."""

import sys
import time
import os
import re
import resource

from PyQt6.QtWidgets import QApplication, QPlainTextEdit
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QTextCursor

from src.main_window import MainWindow


def get_memory_mb():
    """Get current process physical memory in MB (macOS/Linux)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in bytes on macOS
    return usage.ru_maxrss / (1024 * 1024)


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
    t_open = (time.perf_counter() - t_start) * 1000

    large_mode = editor.is_large_file_mode()
    mode_str = " [LARGE FILE MODE]" if large_mode else ""
    print(f"\n  Open file: {t_open:.1f}ms{mode_str}")

    if large_mode:
        # Avoid reading entire file into Python string for large files
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

    # 3. Find-replace "while" -> "for"
    search_text = "while"

    if large_mode:
        # Use backend for counting
        t_start = time.perf_counter()
        match_count = editor.count_matches_in_file(search_text, True, False)
        t_count = (time.perf_counter() - t_start) * 1000
        print(f"\n  Find 'while' matches: {match_count:,} ({t_count:.1f}ms)")

        # Use backend for replace-all
        t_start = time.perf_counter()
        replace_count = editor.replace_all_in_file(search_text, "for", True, False)
        app.processEvents()
        total_replace = (time.perf_counter() - t_start) * 1000
        print(f"  Replace all (backend): {replace_count:,} replacements ({total_replace:.1f}ms)")
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

    # 4. Memory usage
    mem_mb = get_memory_mb()
    print(f"\n  Memory (physical): {mem_mb:.0f} MB ({mem_mb/1024:.2f} GB)")

    window.close()
    del window
    app.processEvents()

    return {
        'file': filename,
        'open_ms': t_open,
        'scroll_max_ms': max_scroll,
        'scroll_avg_ms': avg_scroll,
        'replace_matches': replace_count,
        'replace_total_ms': total_replace,
        'memory_mb': mem_mb,
    }


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


if __name__ == '__main__':
    main()
