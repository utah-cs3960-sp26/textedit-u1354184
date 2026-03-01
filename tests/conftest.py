"""Global test configuration - prevents any Qt dialog from blocking tests."""

import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QMessageBox


@pytest.fixture(autouse=True)
def _no_blocking_dialogs(monkeypatch):
    """Automatically prevent all Qt dialogs from appearing during tests.

    Any test that needs a specific dialog return value should use
    unittest.mock.patch to override these defaults.
    """
    # QMessageBox static methods
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Discard,
    )
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QMessageBox.warning",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QMessageBox.information",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QMessageBox.critical",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QMessageBox.about",
        lambda *args, **kwargs: None,
    )

    # QFileDialog static methods
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("", ""),
    )
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: ("", ""),
    )
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: "",
    )

    # QInputDialog static methods
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QInputDialog.getInt",
        lambda *args, **kwargs: (0, False),
    )
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QInputDialog.getText",
        lambda *args, **kwargs: ("", False),
    )
