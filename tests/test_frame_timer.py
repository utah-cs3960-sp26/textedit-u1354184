"""Tests for the FrameTimerWidget and FrameTimerFilter."""

import pytest
import time

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from src.frame_timer import FrameTimerWidget, FrameTimerFilter


@pytest.fixture(scope="session")
def app():
    """Create a QApplication instance for the test session."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def frame_timer(app):
    """Create a FrameTimerWidget instance."""
    widget = FrameTimerWidget()
    yield widget
    widget.deleteLater()


class TestFrameTimerWidget:
    """Test FrameTimerWidget functionality."""

    def test_initial_state_hidden(self, frame_timer):
        """Test that widget starts hidden."""
        assert not frame_timer.isVisible()
        assert not frame_timer._active

    def test_initial_display(self, frame_timer):
        """Test initial display text."""
        assert "Frame: --" in frame_timer.text()

    def test_toggle_on(self, frame_timer):
        """Test toggling timer on."""
        frame_timer.toggle()
        assert frame_timer.isVisible()
        assert frame_timer._active

    def test_toggle_off(self, frame_timer):
        """Test toggling timer off."""
        frame_timer.toggle()  # on
        frame_timer.toggle()  # off
        assert not frame_timer.isVisible()
        assert not frame_timer._active

    def test_toggle_resets_timings(self, frame_timer):
        """Test that toggling resets timings."""
        frame_timer._record_frame(5.0)
        frame_timer.toggle()  # on (resets)
        assert len(frame_timer._frame_times) == 0
        assert frame_timer._max_time == 0.0

    def test_record_frame(self, frame_timer):
        """Test recording a frame time."""
        frame_timer._record_frame(16.7)
        assert len(frame_timer._frame_times) == 1
        assert frame_timer._frame_times[-1] == 16.7

    def test_record_frame_updates_max(self, frame_timer):
        """Test that max time is tracked."""
        frame_timer._record_frame(5.0)
        frame_timer._record_frame(20.0)
        frame_timer._record_frame(10.0)
        assert frame_timer._max_time == 20.0

    def test_display_updates_after_record(self, frame_timer):
        """Test display text updates after recording."""
        frame_timer._record_frame(10.0)
        text = frame_timer.text()
        assert "10.0ms" in text

    def test_display_shows_average(self, frame_timer):
        """Test display shows correct average."""
        frame_timer._record_frame(10.0)
        frame_timer._record_frame(20.0)
        text = frame_timer.text()
        assert "Avg: 15.0ms" in text

    def test_reset(self, frame_timer):
        """Test _reset clears all data."""
        frame_timer._record_frame(5.0)
        frame_timer._record_frame(10.0)
        frame_timer._reset()
        assert len(frame_timer._frame_times) == 0
        assert frame_timer._max_time == 0.0
        assert "Frame: --" in frame_timer.text()

    def test_install(self, frame_timer, app):
        """Test installing event filter on app."""
        frame_timer.install(app)
        # Should not raise


class TestFrameTimerFilter:
    """Test the FrameTimerFilter event filter."""

    def test_filter_ignores_when_inactive(self, frame_timer, app):
        """Test that filter ignores events when widget is not active."""
        frame_timer._active = False
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        result = frame_timer._filter.eventFilter(app, event)
        assert result is False

    def test_filter_starts_timing_on_user_event(self, frame_timer, app):
        """Test that filter starts timing on user events when active."""
        frame_timer._active = True
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        frame_timer._filter.eventFilter(app, event)
        assert frame_timer._filter._timing is True

    def test_filter_does_not_restart_during_timing(self, frame_timer, app):
        """Test that filter doesn't restart if already timing."""
        frame_timer._active = True
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        frame_timer._filter.eventFilter(app, event)
        start_time = frame_timer._filter._frame_start

        # Second event should not restart timing
        event2 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_B, Qt.KeyboardModifier.NoModifier)
        frame_timer._filter.eventFilter(app, event2)
        assert frame_timer._filter._frame_start == start_time

    def test_frame_end_records(self, frame_timer):
        """Test that _on_frame_end records a frame time."""
        frame_timer._filter._timing = True
        frame_timer._filter._frame_start = time.perf_counter() - 0.01  # 10ms ago
        frame_timer._filter._on_frame_end()
        assert not frame_timer._filter._timing
        assert len(frame_timer._frame_times) == 1
        assert frame_timer._frame_times[-1] >= 9.0  # At least ~10ms

    def test_frame_end_noop_when_not_timing(self, frame_timer):
        """Test that _on_frame_end does nothing when not timing."""
        frame_timer._filter._timing = False
        frame_timer._filter._on_frame_end()
        assert len(frame_timer._frame_times) == 0
