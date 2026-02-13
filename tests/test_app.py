"""Tests for the application entry point."""

import pytest
from unittest.mock import patch, MagicMock


def test_main_function():
    """Test the main function runs without error."""
    with patch('src.app.QApplication') as mock_app_class, \
         patch('src.app.MainWindow') as mock_window_class, \
         patch('src.app.sys') as mock_sys:

        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 0

        mock_window = MagicMock()
        mock_window_class.return_value = mock_window

        from src.app import main
        main()

        mock_app_class.assert_called_once()
        mock_app.setApplicationName.assert_called_with("TextEdit")
        mock_app.setApplicationVersion.assert_called_with("0.1.0")
        mock_window.show.assert_called_once()
        mock_sys.exit.assert_called_once()
