# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:47 CET: Copilot: Tested GUI command recording and script output
# 2026-11-22 19:40 CET: Copilot: Tested end-to-end Calculate action

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

REFERENCE_SCRIPT = (
    Path(__file__).parent
    / "reference"
    / "simply_supported_beam"
    / "simply_supported_beam_heb300.mfs"
)


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


def test_calculate_creates_same_basename_outputs(
    qapp: QApplication, tmp_path: Path
) -> None:
    script_path = tmp_path / "beam.mfs"
    window = MainWindow()
    window.current_script = script_path
    window.script_editor.setPlainText(REFERENCE_SCRIPT.read_text(encoding="utf-8"))

    QTest.mouseClick(window.calculate_button, Qt.MouseButton.LeftButton)

    assert script_path.is_file()
    assert script_path.with_suffix(".json").is_file()
    assert script_path.with_suffix(".py").is_file()
    output = script_path.with_suffix(".out").read_text(encoding="utf-8")
    assert "My max/min: 80.00 / 0.00 kNm" in output
    assert "dz max: 10.09 mm" in output
    window.close()
