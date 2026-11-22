# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:47 CET: Copilot: Tested GUI command recording and script output

import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from myfem.gui.main_window import MainWindow
from myfem.script import write_model


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_gui_command_is_saved_and_generates_json(
    qapp: QApplication, tmp_path: Path
) -> None:
    window = MainWindow()
    window.command_input.setText("node N1 x=0 y=0 z=0")

    QTest.mouseClick(window.add_button, Qt.MouseButton.LeftButton)

    script_path = tmp_path / "model.mfs"
    assert window._save_to(script_path)
    assert script_path.read_text(encoding="utf-8").strip() == ("node N1 x=0 y=0 z=0")

    output_path = tmp_path / "model.json"
    write_model(script_path, output_path)
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["nodes"] == [{"id": "N1", "x": 0.0, "y": 0.0, "z": 0.0}]
    window.close()
