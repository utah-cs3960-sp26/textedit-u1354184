"""Frame timer widget for measuring editor responsiveness."""

import time
from collections import deque

from PyQt6.QtWidgets import QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer, QObject, QEvent


class FrameTimerFilter(QObject):
    """Event filter that measures frame timings, excluding idle time."""

    # Events that represent user interaction (not idle)
    USER_EVENTS = {
        QEvent.Type.KeyPress, QEvent.Type.KeyRelease,
        QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
        QEvent.Type.MouseMove, QEvent.Type.MouseButtonDblClick,
        QEvent.Type.Wheel, QEvent.Type.Scroll,
        QEvent.Type.ShortcutOverride, QEvent.Type.Shortcut,
        QEvent.Type.InputMethod,
        QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop,
        QEvent.Type.Resize,
    }

    def __init__(self, widget):
        super().__init__()
        self._widget = widget
        self._timing = False
        self._frame_start = 0.0
        self._end_timer = QTimer()
        self._end_timer.setSingleShot(True)
        self._end_timer.setInterval(0)
        self._end_timer.timeout.connect(self._on_frame_end)

    def eventFilter(self, obj, event):
        if not self._widget._active:
            return False

        etype = event.type()
        if etype in self.USER_EVENTS and not self._timing:
            self._timing = True
            self._frame_start = time.perf_counter()
            # Schedule end-of-frame callback; fires after all pending events
            # (including paints) are processed
            self._end_timer.start()
        return False

    def _on_frame_end(self):
        if self._timing:
            elapsed_ms = (time.perf_counter() - self._frame_start) * 1000.0
            self._timing = False
            self._widget._record_frame(elapsed_ms)


class FrameTimerWidget(QLabel):
    """Displays last, average, and max frame timings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._frame_times = deque(maxlen=300)
        self._max_time = 0.0

        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setStyleSheet(
            "QLabel { background: #222; color: #0f0; padding: 2px 8px; "
            "font-family: Menlo, monospace; font-size: 11px; }"
        )
        self._update_display()
        self.hide()

        self._filter = FrameTimerFilter(self)

    def install(self, app: QApplication):
        """Install the event filter on the application."""
        app.installEventFilter(self._filter)

    def toggle(self):
        """Toggle visibility. Resets timings on hide."""
        if self.isVisible():
            self._active = False
            self._reset()
            self.hide()
        else:
            self._reset()
            self._active = True
            self.show()

    def _reset(self):
        """Reset all recorded timings."""
        self._frame_times.clear()
        self._max_time = 0.0
        self._update_display()

    def _record_frame(self, ms: float):
        """Record a frame time in milliseconds."""
        self._frame_times.append(ms)
        if ms > self._max_time:
            self._max_time = ms
        self._update_display()

    def _update_display(self):
        """Update the label text with current timings."""
        if not self._frame_times:
            self.setText("Frame: --  Avg: --  Max: --")
            return

        last = self._frame_times[-1]
        avg = sum(self._frame_times) / len(self._frame_times)
        mx = self._max_time

        self.setText(f"Frame: {last:.1f}ms  Avg: {avg:.1f}ms  Max: {mx:.1f}ms")
