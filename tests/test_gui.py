# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:47 CET: Copilot: Tested GUI command recording and script output
# 2026-11-22 19:40 CET: Copilot: Tested end-to-end Calculate action
# 2026-11-22 21:20 CET: Copilot: Tested toolbar icons and new/save actions
# 2026-11-23 19:32 CET: Copilot: Verified actions in top toolbar
# 2026-11-23 19:37 CET: Copilot: Tested Help attributions and update details
# 2026-11-23 20:45 CET: Copilot: Checked safety heading in About dialog
# 2026-11-23 20:50 CET: Copilot: Checked AI disclosure in About dialog
# 2026-11-23 21:17 CET: Copilot: Tested model-entry toolbar dialogs
# 2026-11-23 22:17 CET: Copilot: Tested Wayland warning filter configuration
# 2026-11-23 23:41 CET: Copilot: Tested support marker and node-label spacing

import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QMessageBox,
    QTextBrowser,
)

from myfem.gui.__main__ import _configure_wayland_textinput_logging
from myfem.gui.main_window import MainWindow, _application_version
from myfem.script import compile_commands

REFERENCE_SCRIPT = (
    Path(__file__).parent
    / "reference"
    / "simply_supported_beam"
    / "simply_supported_beam_heb300.mfs"
)


def test_wayland_textinput_filter_respects_existing_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("QT_LOGGING_RULES", "qt.qml.*=false")

    _configure_wayland_textinput_logging()

    assert os.environ["QT_LOGGING_RULES"] == (
        "qt.qml.*=false;qt.qpa.wayland.textinput.warning=false"
    )

    monkeypatch.setenv("QT_LOGGING_RULES", "qt.qpa.wayland.textinput.warning=true")
    _configure_wayland_textinput_logging()
    assert os.environ["QT_LOGGING_RULES"] == "qt.qpa.wayland.textinput.warning=true"


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

    output_path = script_path.with_suffix(".json")
    assert output_path.is_file()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["nodes"] == [{"id": "N1", "x": 0.0, "y": 0.0, "z": 0.0}]
    window.close()


def test_toolbar_icons_load_and_new_clears_document(
    qapp: QApplication, tmp_path: Path
) -> None:
    window = MainWindow()
    window.current_script = tmp_path / "existing.mfs"
    window.script_editor.setPlainText("node N1 x=0 y=0 z=0")
    window.command_input.setText("node N2 x=1 y=0 z=0")
    window.script_editor.document().setModified(False)

    assert window.toolBarArea(window.file_toolbar) == Qt.ToolBarArea.TopToolBarArea
    for action in (
        window.new_action,
        window.open_action,
        window.save_action,
        window.add_node_action,
        window.add_member_action,
        window.add_support_action,
        window.add_load_action,
        window.calculate_action,
    ):
        assert not action.icon().isNull()
        assert window.file_toolbar.widgetForAction(action) is not None
    assert window.file_toolbar.actions() == [
        window.new_action,
        window.open_action,
        window.save_action,
        window.add_node_action,
        window.add_member_action,
        window.add_support_action,
        window.add_load_action,
        window.calculate_action,
    ]

    window.new_action.trigger()

    assert window.script_editor.toPlainText() == ""
    assert window.command_input.text() == ""
    assert window.current_script is None
    assert not window.script_editor.document().isModified()

    new_script_path = tmp_path / "new_model.mfs"
    assert window._save_to(new_script_path)
    model = json.loads(new_script_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert model["nodes"] == []
    window.close()


def test_toolbar_dialogs_append_complete_model_commands(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()

    def accept_dialog(dialog: QDialog) -> QDialog.DialogCode:
        dialog_name = dialog.objectName()
        if dialog_name == "add_node_dialog":
            y_field = dialog.findChild(QDoubleSpinBox, "node_y")
            assert y_field is not None
            assert y_field.isReadOnly()
            if window.script_editor.toPlainText():
                x_field = dialog.findChild(QDoubleSpinBox, "node_x")
                assert x_field is not None
                x_field.setValue(8)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", accept_dialog)
    window.add_node_action.trigger()
    window.add_node_action.trigger()
    window.add_member_action.trigger()
    window.add_support_action.trigger()
    window.add_load_action.trigger()

    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=0 y=0 z=0",
        "node N2 x=8 y=0 z=0",
        "member M1 N1 N2 material=default section=default",
        "support N1 DX=true DY=true DZ=true RX=true RY=false RZ=true",
        (
            "load distributed M1 direction=FZ value_start=10000 value_end=10000 "
            "position_start=0 position_end=8 case=default"
        ),
    ]
    window.script_editor.document().setModified(False)
    window.close()


def test_2d_canvas_adds_snapped_nodes_and_member(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    qapp.processEvents()

    QTest.mouseClick(window.node_tool_button, Qt.MouseButton.LeftButton)
    for x, z in ((1.24, -0.74), (4.1, -0.24)):
        position = window.canvas_2d.mapFromScene(QPointF(x * 30, z * 30))
        QTest.mouseClick(
            window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=position
        )

    QTest.mouseClick(window.member_tool_button, Qt.MouseButton.LeftButton)
    for x, z in ((1.0, -0.5), (4.0, 0.0)):
        position = window.canvas_2d.mapFromScene(QPointF(x * 30, z * 30))
        QTest.mouseClick(
            window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=position
        )

    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=1 y=0 z=-0.5",
        "node N2 x=4 y=0 z=0",
        "member M1 N1 N2 material=default section=default",
    ]
    window.script_editor.document().setModified(False)
    window.close()


def test_2d_reference_fiber_points_below_and_right(qapp: QApplication) -> None:
    window = MainWindow()
    model = compile_commands(
        "node H1 x=0 y=0 z=0\n"
        "node H2 x=2 y=0 z=0\n"
        "node V1 x=3 y=0 z=2\n"
        "node V2 x=3 y=0 z=0\n"
        "node L1 x=0 y=0 z=4\n"
        "node L2 x=8 y=0 z=4\n"
        "member MH H1 H2\n"
        "member MV V1 V2\n"
        "member ML L1 L2"
    )
    window.canvas_2d.set_model(model)

    fiber_lines = [
        item
        for item in window.canvas_2d.scene().items()
        if isinstance(item, QGraphicsLineItem)
        and item.pen().color().name() == "#747c85"
    ]
    member_lines = [
        item
        for item in window.canvas_2d.scene().items()
        if isinstance(item, QGraphicsLineItem)
        and item.pen().color().name() == "#26384d"
    ]
    axis_lines = [
        item
        for item in window.canvas_2d.scene().items()
        if isinstance(item, QGraphicsLineItem)
        and item.pen().color().name() == "#b4c0cc"
    ]

    assert len(fiber_lines) == 9
    assert len(member_lines) == 3
    assert len(axis_lines) == 2
    assert member_lines[0].pen().widthF() > axis_lines[0].pen().widthF()
    assert all(
        fiber.pen().widthF() < member_lines[0].pen().widthF() for fiber in fiber_lines
    )
    assert (
        member_lines[0].pen().color().lightness()
        < axis_lines[0].pen().color().lightness()
    )
    horizontal_fibers = [
        item for item in fiber_lines if item.line().y1() == pytest.approx(7)
    ]
    vertical_fibers = [
        item for item in fiber_lines if item.line().x1() == pytest.approx(97)
    ]
    long_member_fibers = [
        item for item in fiber_lines if item.line().y1() == pytest.approx(127)
    ]
    assert len(horizontal_fibers) == len(vertical_fibers) == 3
    assert len(long_member_fibers) == 3
    assert sum(
        (item.line().x1() + item.line().x2()) / 2 for item in horizontal_fibers
    ) / 3 == pytest.approx(30)
    assert sum(
        (item.line().y1() + item.line().y2()) / 2 for item in vertical_fibers
    ) / 3 == pytest.approx(30)
    assert sum(
        (item.line().x1() + item.line().x2()) / 2 for item in long_member_fibers
    ) / 3 == pytest.approx(120)
    assert max(item.line().x2() - item.line().x1() for item in long_member_fibers) > (
        max(item.line().x2() - item.line().x1() for item in horizontal_fibers)
    )
    window.close()


def test_2d_canvas_draws_pin_roller_and_fixed_supports(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    model = compile_commands(
        "node P x=0 y=0 z=0\n"
        "node R x=1 y=0 z=0\n"
        "node F x=2 y=0 z=0\n"
        "support P DX=true DY=true DZ=true RX=true RY=false RZ=true\n"
        "support R DX=false DY=true DZ=true RX=true RY=false RZ=true\n"
        "support F DX=true DY=true DZ=true RX=true RY=true RZ=true"
    )
    window.canvas_2d.set_model(model)
    scene_items = window.canvas_2d.scene().items()

    assert sum(isinstance(item, QGraphicsPolygonItem) for item in scene_items) == 1
    assert sum(isinstance(item, QGraphicsRectItem) for item in scene_items) == 1
    assert sum(isinstance(item, QGraphicsEllipseItem) for item in scene_items) == 5
    window.close()


def test_dx_and_rotation_support_symbols_do_not_overlap_node_label(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    model = compile_commands(
        "node N1 x=0 y=0 z=0\n"
        "support N1 DX=true DY=true DZ=false RX=true RY=true RZ=true"
    )
    window.canvas_2d.set_model(model)
    scene_items = window.canvas_2d.scene().items()
    labels = {
        item.text(): item
        for item in scene_items
        if isinstance(item, QGraphicsSimpleTextItem)
    }

    assert "N1" in labels
    assert "RY" in labels
    assert (
        not labels["N1"]
        .sceneBoundingRect()
        .intersects(labels["RY"].sceneBoundingRect())
    )
    support_items = [
        item
        for item in scene_items
        if isinstance(item, (QGraphicsEllipseItem, QGraphicsLineItem))
        and item.pen().color().name() == "#46525e"
    ]
    assert all(
        not labels["N1"].sceneBoundingRect().intersects(item.sceneBoundingRect())
        for item in support_items
    )
    window.close()


def test_help_menu_shows_attributions_version_and_manual_update(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    assert window.help_menu.title() == "&Help"
    assert [action.text() for action in window.help_menu.actions()] == [
        "&Update instructions...",
        "&About MyFEM",
        "",
        "MyFEM on &GitHub",
    ]

    about_content: dict[str, str] = {}

    def inspect_about_dialog(dialog: QDialog) -> QDialog.DialogCode:
        browser = dialog.findChild(QTextBrowser)
        assert browser is not None
        assert browser.openExternalLinks()
        about_content["html"] = browser.toHtml()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", inspect_about_dialog)
    window.about_action.trigger()
    about_html = about_content["html"]
    assert _application_version() in about_html
    assert "Johannes Kalliauer" in about_html
    assert "GNU GPLv3" in about_html
    assert "D. Craig Brinck" in about_html
    assert "Craig (@JWock82)" in about_html
    assert "MIT" in about_html
    assert "contributor list" in about_html
    assert "@ndre@s" in about_html
    assert "CC BY-SA 3.0" in about_html
    assert "CC BY-SA 4.0" in about_html
    assert "AI disclosure" in about_html
    assert "majority of MyFEM" in about_html
    assert "LLM-based AI" in about_html
    assert "Safety and liability" in about_html

    messages: dict[str, str] = {}
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda _parent, _title, text: messages.update(update=text),
    )
    window.update_action.trigger()

    assert _application_version() in messages["update"]
    assert "git pull --ff-only" in messages["update"]
    assert "not installed automatically" in messages["update"]
    window.close()


def test_calculate_creates_same_basename_outputs(
    qapp: QApplication, tmp_path: Path
) -> None:
    script_path = tmp_path / "beam.mfs"
    window = MainWindow()
    window.current_script = script_path
    window.script_editor.setPlainText(REFERENCE_SCRIPT.read_text(encoding="utf-8"))

    window.calculate_action.trigger()

    assert script_path.is_file()
    assert script_path.with_suffix(".json").is_file()
    assert script_path.with_suffix(".py").is_file()
    output = script_path.with_suffix(".out").read_text(encoding="utf-8")
    assert "My max/min: 80.00 / 0.00 kNm" in output
    assert "dz max: 10.09 mm" in output
    window.close()
