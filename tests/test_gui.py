# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-24 22:02 CET: Copilot: Tested beam terminology and B-series IDs
# 2026-11-24 22:30 CET: Copilot: Tested double-click node coordinate editing
# 2026-11-24 22:40 CET: Copilot: Tested undo toolbar and undoable model edits
# 2026-11-24 22:50 CET: Copilot: Tested beam and support selection and editing
# 2026-11-24 23:05 CET: Copilot: Tested node-on-beam confirmation and undo
# 2026-11-24 23:15 CET: Copilot: Tested context menus and new-file metadata
# 2026-11-24 23:24 CET: Copilot: Tested canvas zoom and concise node deletion
# 2026-11-24 23:39 CET: Copilot: Tests coordinated application and format versions
# 2026-11-24 23:47 CET: Copilot: Tests timestamped save filename suggestion
# 2026-11-24 23:51 CET: Copilot: Tests the Yes-first split confirmation

import json
import os
import re
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTextBrowser,
)

from myfem.gui.__main__ import _configure_wayland_textinput_logging
from myfem.gui.main_window import MainWindow, _application_version
from myfem.script import compile_commands
from myfem.versioning import FORMAT_VERSION

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
    window.command_input.setText("node N1 x=0 z=0")

    QTest.mouseClick(window.add_button, Qt.MouseButton.LeftButton)

    script_path = tmp_path / "model.mfs"
    assert window._save_to(script_path)
    saved_lines = script_path.read_text(encoding="utf-8").splitlines()
    assert saved_lines[0].startswith("# Created with MyFEM GUI version ")
    assert f"format_version={FORMAT_VERSION}" in saved_lines[0]
    assert saved_lines[1].startswith("# Created: ")
    assert saved_lines[2] == "model 2D xz x=right z=down"
    assert saved_lines[3] == "node N1 x=0 z=0"

    output_path = script_path.with_suffix(".json")
    assert output_path.is_file()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["nodes"] == [{"id": "N1", "x": 0.0, "y": 0.0, "z": 0.0}]
    assert window.script_editor.toPlainText().splitlines() == saved_lines
    window.close()


def test_saving_an_opened_script_does_not_add_new_file_metadata(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script_path = tmp_path / "existing.mfs"
    original = "node N1 x=0 z=0"
    script_path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *_args: (str(script_path), ""),
    )
    window = MainWindow()

    window.open_script()
    assert not window._new_model
    assert window._save_to(script_path)

    saved = script_path.read_text(encoding="utf-8")
    assert saved == f"{original}\n"
    assert "# Created with MyFEM GUI" not in saved
    window.close()


def test_new_model_suggests_timestamped_mfs_filename(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    suggested_paths: list[str] = []

    def cancel_save_dialog(*args: object) -> tuple[str, str]:
        suggested_paths.append(str(args[2]))
        return "", ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", cancel_save_dialog)
    window = MainWindow()

    assert not window.save_script_as()
    assert re.fullmatch(
        r"MyFEM-Model-\d{4}-\d{2}-\d{2}_\d{2}_\d{2}\.mfs",
        Path(suggested_paths[0]).name,
    )
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
        window.undo_action,
        window.add_node_action,
        window.add_beam_action,
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
        window.undo_action,
        window.add_node_action,
        window.add_beam_action,
        window.add_support_action,
        window.add_load_action,
        window.calculate_action,
    ]

    window.new_action.trigger()

    assert window.script_editor.toPlainText() == ""
    assert window.command_input.text() == ""
    assert window.current_script is None
    assert window._new_model
    assert not window.script_editor.document().isModified()

    new_script_path = tmp_path / "new_model.mfs"
    assert window._save_to(new_script_path)
    model = json.loads(new_script_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert model["nodes"] == []
    window.close()


def test_undo_toolbar_action_reverts_a_recorded_command(qapp: QApplication) -> None:
    window = MainWindow()
    assert not window.undo_action.isEnabled()

    assert window._append_model_command("node N1 x=0 y=0 z=0", "Could not add node")
    assert window.script_editor.toPlainText() == "node N1 x=0 y=0 z=0"
    assert window.undo_action.isEnabled()

    window.undo_action.trigger()

    assert window.script_editor.toPlainText() == ""
    assert not window.undo_action.isEnabled()
    assert not window.script_editor.document().isModified()
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
    window.add_node()
    window.add_node()
    window.add_beam()
    window.add_support()
    window.add_distributed_load()

    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=0 z=0",
        "node N2 x=8 z=0",
        "beam B1 N1 N2",
        "support N1 DX=true DZ=true RY=false",
        (
            "load distributed B1 direction=FZ value_start=10000 value_end=10000 "
            "position_start=0 position_end=8 case=default"
        ),
    ]
    window.script_editor.document().setModified(False)
    window.close()


def test_model_toolbar_icons_use_left_click_for_graphics_and_right_for_dialogs(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    window.show()
    qapp.processEvents()
    dialog_requests: list[str] = []
    monkeypatch.setattr(window, "add_node", lambda: dialog_requests.append("node"))
    monkeypatch.setattr(window, "add_beam", lambda: dialog_requests.append("beam"))

    node_icon = window.file_toolbar.widgetForAction(window.add_node_action)
    beam_icon = window.file_toolbar.widgetForAction(window.add_beam_action)
    assert node_icon is not None
    assert beam_icon is not None

    QTest.mouseClick(node_icon, Qt.MouseButton.LeftButton)
    assert window.canvas_2d.mode == "node"
    assert dialog_requests == []
    QTest.mouseClick(node_icon, Qt.MouseButton.RightButton)
    assert dialog_requests == ["node"]

    QTest.mouseClick(beam_icon, Qt.MouseButton.LeftButton)
    assert window.canvas_2d.mode == "beam"
    QTest.mouseClick(beam_icon, Qt.MouseButton.RightButton)
    assert dialog_requests == ["node", "beam"]

    window.close()


def test_2d_canvas_adds_snapped_nodes_and_beam(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    qapp.processEvents()

    node_icon = window.file_toolbar.widgetForAction(window.add_node_action)
    assert node_icon is not None
    QTest.mouseClick(node_icon, Qt.MouseButton.LeftButton)
    for x, z in ((1.24, -0.74), (4.1, -0.24)):
        position = window.canvas_2d.mapFromScene(QPointF(x * 30, z * 30))
        QTest.mouseClick(
            window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=position
        )

    beam_icon = window.file_toolbar.widgetForAction(window.add_beam_action)
    assert beam_icon is not None
    QTest.mouseClick(beam_icon, Qt.MouseButton.LeftButton)
    for x, z in ((1.0, -0.5), (4.0, 0.0)):
        position = window.canvas_2d.mapFromScene(QPointF(x * 30, z * 30))
        QTest.mouseClick(
            window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=position
        )

    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=1 z=-0.5",
        "node N2 x=4 z=0",
        "beam B1 N1 N2",
    ]
    window.script_editor.document().setModified(False)
    window.close()


def test_2d_canvas_zooms_with_mouse_wheel(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    qapp.processEvents()
    canvas = window.canvas_2d
    initial_scale = canvas.transform().m11()
    local_position = QPointF(canvas.viewport().rect().center())
    global_position = QPointF(canvas.viewport().mapToGlobal(local_position.toPoint()))

    def send_wheel(delta: int) -> None:
        event = QWheelEvent(
            local_position,
            global_position,
            QPoint(),
            QPoint(0, delta),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate,
            False,
        )
        QApplication.sendEvent(canvas.viewport(), event)
        assert event.isAccepted()

    send_wheel(120)
    zoomed_scale = canvas.transform().m11()
    assert zoomed_scale > initial_scale

    send_wheel(-120)
    assert canvas.transform().m11() == pytest.approx(initial_scale)
    window.close()


def test_adding_node_on_beam_prompts_and_splits_undoably(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = "node N1 x=0 y=0 z=0\nnode N2 x=4 y=0 z=0\nbeam B1 N1 N2"
    window = MainWindow()
    window.script_editor.setPlainText(source)
    window.script_editor.document().setModified(False)
    window.show()
    qapp.processEvents()
    questions: list[str] = []

    def confirm_split(dialog: QDialog) -> QDialog.DialogCode:
        assert dialog.objectName() == "split_beam_dialog"
        question = dialog.findChild(QLabel, "split_beam_question")
        yes_button = dialog.findChild(QPushButton, "split_beam_yes")
        no_button = dialog.findChild(QPushButton, "split_beam_no")
        button_row = dialog.findChild(QHBoxLayout, "split_beam_button_row")
        assert question is not None
        assert yes_button is not None
        assert no_button is not None
        assert button_row is not None
        assert button_row.itemAt(1).widget() is yes_button
        assert button_row.itemAt(2).widget() is no_button
        assert yes_button.isDefault()
        questions.append(question.text())
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", confirm_split)
    node_icon = window.file_toolbar.widgetForAction(window.add_node_action)
    assert node_icon is not None
    QTest.mouseClick(node_icon, Qt.MouseButton.LeftButton)
    node_position = window.canvas_2d.mapFromScene(QPointF(60, 0))
    QTest.mouseClick(
        window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=node_position
    )

    assert len(questions) == 1
    assert "B1" in questions[0]
    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=0 y=0 z=0",
        "node N2 x=4 y=0 z=0",
        "node N3 x=2 z=0",
        "beam B1a N1 N3",
        "beam B1b N3 N2",
    ]
    model = compile_commands(window.script_editor.toPlainText())
    assert [beam["id"] for beam in model["beams"]] == ["B1a", "B1b"]

    window.undo_action.trigger()
    assert window.script_editor.toPlainText() == source
    assert not window.script_editor.document().isModified()
    window.close()


def test_declining_beam_split_adds_only_the_node(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    window.script_editor.setPlainText(
        "node N1 x=0 y=0 z=0\nnode N2 x=4 y=0 z=0\nbeam B1 N1 N2"
    )
    window.script_editor.document().setModified(False)
    monkeypatch.setattr(
        QDialog,
        "exec",
        lambda _dialog: QDialog.DialogCode.Rejected,
    )

    window._record_new_node("N3", 2, 0, "node N3 x=2 y=0 z=0")

    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=0 y=0 z=0",
        "node N2 x=4 y=0 z=0",
        "beam B1 N1 N2",
        "node N3 x=2 y=0 z=0",
    ]
    window.script_editor.document().setModified(False)
    window.close()


def test_node_context_menu_deletes_node_and_connected_model_objects(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = (
        "node N1 x=0 z=0\n"
        "node N2 x=4 z=0\n"
        "beam B1 N1 N2\n"
        "load distributed B1 direction=FZ value_start=1 value_end=1 "
        "position_start=0 position_end=4 case=default\n"
        "support N1 DX=true DZ=true RY=false"
    )
    window = MainWindow()
    window.script_editor.setPlainText(source)
    window.script_editor.document().setModified(False)
    window.show()
    qapp.processEvents()

    def delete_from_menu(menu: QMenu, _position: object) -> None:
        action = next(
            action
            for action in menu.actions()
            if action.objectName() == "delete_node_context_action"
        )
        assert action.text() == "Delete node"
        action.trigger()

    monkeypatch.setattr(window, "_execute_context_menu", delete_from_menu)
    node_position = window.canvas_2d.mapFromScene(QPointF(0, 0))
    QTest.mouseClick(
        window.canvas_2d.viewport(), Qt.MouseButton.RightButton, pos=node_position
    )

    model = compile_commands(window.script_editor.toPlainText())
    assert [node["id"] for node in model["nodes"]] == ["N2"]
    assert model["beams"] == []
    assert model["loads"] == []
    assert model["supports"] == []
    window.undo_action.trigger()
    assert window.script_editor.toPlainText() == source
    window.script_editor.document().setModified(False)
    window.close()


def test_node_context_menu_creates_or_edits_support_at_that_node(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    window.script_editor.setPlainText("node N1 x=0 z=0")
    window.script_editor.document().setModified(False)
    window.show()
    qapp.processEvents()
    support_actions: list[str] = []

    def create_support_from_menu(menu: QMenu, _position: object) -> None:
        action = next(
            action
            for action in menu.actions()
            if action.objectName() == "support_context_action"
        )
        support_actions.append(action.text())
        action.trigger()

    def accept_support_dialog(dialog: QDialog) -> QDialog.DialogCode:
        if dialog.objectName() == "add_support_dialog":
            node = dialog.findChild(QComboBox, "support_node")
            assert node is not None
            assert node.currentText() == "N1"
        else:
            assert dialog.objectName() == "edit_support_dialog"
            ry = dialog.findChild(QCheckBox, "edit_support_ry")
            assert ry is not None
            ry.setChecked(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(window, "_execute_context_menu", create_support_from_menu)
    monkeypatch.setattr(QDialog, "exec", accept_support_dialog)
    node_position = window.canvas_2d.mapFromScene(QPointF(0, 0))
    QTest.mouseClick(
        window.canvas_2d.viewport(), Qt.MouseButton.RightButton, pos=node_position
    )
    QTest.mouseClick(
        window.canvas_2d.viewport(), Qt.MouseButton.RightButton, pos=node_position
    )

    assert support_actions == ["Add support", "Edit support"]
    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=0 z=0",
        "support N1 DX=true DZ=true RY=true",
    ]
    window.script_editor.document().setModified(False)
    window.close()


def test_editing_support_with_all_2d_restraints_free_removes_it(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = "node N1 x=0 z=0\nsupport N1 DX=true DZ=true RY=false"
    window = MainWindow()
    window.script_editor.setPlainText(original)
    window.script_editor.document().setModified(False)

    def release_support(dialog: QDialog) -> QDialog.DialogCode:
        assert dialog.objectName() == "edit_support_dialog"
        for field_name in (
            "edit_support_dx",
            "edit_support_dz",
            "edit_support_ry",
        ):
            field = dialog.findChild(QCheckBox, field_name)
            assert field is not None
            field.setChecked(False)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", release_support)
    window.edit_support("N1")

    assert window.script_editor.toPlainText() == "node N1 x=0 z=0"
    window.undo_action.trigger()
    assert window.script_editor.toPlainText() == original
    window.script_editor.document().setModified(False)
    window.close()


def test_adding_support_with_all_2d_restraints_free_adds_nothing(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    window.script_editor.setPlainText("node N1 x=0 z=0")
    window.script_editor.document().setModified(False)

    def accept_unrestrained_support(dialog: QDialog) -> QDialog.DialogCode:
        assert dialog.objectName() == "add_support_dialog"
        for field_name in ("support_dx", "support_dz", "support_ry"):
            field = dialog.findChild(QCheckBox, field_name)
            assert field is not None
            field.setChecked(False)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", accept_unrestrained_support)
    window.add_support("N1")

    assert window.script_editor.toPlainText() == "node N1 x=0 z=0"
    assert not window.undo_action.isEnabled()
    window.close()


def test_escape_returns_to_select_mode_from_focused_editor(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    window.show()
    qapp.processEvents()

    node_icon = window.file_toolbar.widgetForAction(window.add_node_action)
    assert node_icon is not None
    QTest.mouseClick(node_icon, Qt.MouseButton.LeftButton)
    assert window.canvas_2d.mode == "node"

    QTest.keyClick(window.script_editor, Qt.Key.Key_Escape)

    assert window.canvas_2d.mode == "select"
    window.close()


def test_double_click_node_edits_coordinates_and_preserves_comment(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    window.script_editor.setPlainText(
        "node N1 x=0 y=0 z=0 # origin\n"
        "node N2 x=2 y=0 z=0\n"
        "beam B1 N1 N2 material=default section=default"
    )
    window.show()
    qapp.processEvents()
    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda _parent, title, text: warnings.append((title, text)),
    )

    def accept_edit(dialog: QDialog) -> QDialog.DialogCode:
        assert dialog.objectName() == "edit_node_dialog"
        x_field = dialog.findChild(QDoubleSpinBox, "edit_node_x")
        z_field = dialog.findChild(QDoubleSpinBox, "edit_node_z")
        assert x_field is not None
        assert z_field is not None
        x_field.setValue(1.5)
        z_field.setValue(0.5)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", accept_edit)
    position = window.canvas_2d.mapFromScene(QPointF(0, 0))
    QTest.mouseDClick(
        window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=position
    )

    assert warnings == []
    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=1.5 z=0.5 # origin",
        "node N2 x=2 y=0 z=0",
        "beam B1 N1 N2 material=default section=default",
    ]
    model = compile_commands(window.script_editor.toPlainText())
    assert model["nodes"][0]["x"] == pytest.approx(1.5)
    assert model["nodes"][0]["z"] == pytest.approx(0.5)
    window.undo_action.trigger()
    assert window.script_editor.toPlainText().splitlines() == [
        "node N1 x=0 y=0 z=0 # origin",
        "node N2 x=2 y=0 z=0",
        "beam B1 N1 N2 material=default section=default",
    ]
    assert not window.script_editor.document().isModified()
    window.close()


def test_selecting_beam_and_support_highlights_each_object(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    window.script_editor.setPlainText(
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=2 y=0 z=0\n"
        "beam B1 N1 N2\n"
        "support N1 DX=true DY=true DZ=true RX=true RY=false RZ=true"
    )
    window.script_editor.document().setModified(False)
    window.show()
    qapp.processEvents()
    selections: list[tuple[str, str]] = []
    window.canvas_2d.object_selected.connect(
        lambda kind, identifier: selections.append((kind, identifier))
    )

    support_position = window.canvas_2d.mapFromScene(QPointF(0, 15))
    QTest.mouseClick(
        window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=support_position
    )
    assert selections[-1] == ("support", "N1")
    assert any(
        isinstance(item, QGraphicsLineItem) and item.pen().color().name() == "#e67700"
        for item in window.canvas_2d.scene().items()
    )

    beam_position = window.canvas_2d.mapFromScene(QPointF(30, 0))
    QTest.mouseClick(
        window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=beam_position
    )
    assert selections[-1] == ("beam", "B1")
    selected_beams = [
        item
        for item in window.canvas_2d.scene().items()
        if isinstance(item, QGraphicsLineItem)
        and item.pen().color().name() == "#e67700"
    ]
    assert len(selected_beams) == 1
    window.close()


def test_double_click_beam_edits_end_node_and_preserves_properties(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    window.script_editor.setPlainText(
        "material steel E=2.1e11 G=8.077e10 nu=0.3 rho=78500\n"
        "section custom A=0.01 I_yy=0.0001 I_zz=0.00005 I_T=0.000001\n"
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=2 y=0 z=0\n"
        "node N3 x=4 y=0 z=0\n"
        "beam B1 N1 N2 material=steel section=custom # keep"
    )
    window.script_editor.document().setModified(False)
    window.show()
    qapp.processEvents()

    def accept_beam_edit(dialog: QDialog) -> QDialog.DialogCode:
        assert dialog.objectName() == "edit_beam_dialog"
        end_node = dialog.findChild(QComboBox, "edit_beam_end_node")
        material = dialog.findChild(QComboBox, "edit_beam_material")
        section = dialog.findChild(QComboBox, "edit_beam_section")
        assert end_node is not None
        assert material is not None
        assert section is not None
        assert material.currentText() == "steel"
        assert section.currentText() == "custom"
        end_node.setCurrentText("N3")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", accept_beam_edit)
    beam_position = window.canvas_2d.mapFromScene(QPointF(30, 0))
    QTest.mouseDClick(
        window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=beam_position
    )

    assert window.script_editor.toPlainText().splitlines()[-1] == (
        "beam B1 N1 N3 material=steel section=custom # keep"
    )
    assert (
        compile_commands(window.script_editor.toPlainText())["beams"][0]["node_end"]
        == "N3"
    )
    window.script_editor.document().setModified(False)
    window.close()


def test_double_click_support_edits_2d_restraint_and_preserves_other_dofs(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    window.script_editor.setPlainText(
        "node N1 x=0 y=0 z=0\n"
        "support N1 DX=true DY=false DZ=true RX=false RY=true RZ=false # keep"
    )
    window.script_editor.document().setModified(False)
    window.show()
    qapp.processEvents()

    def accept_support_edit(dialog: QDialog) -> QDialog.DialogCode:
        assert dialog.objectName() == "edit_support_dialog"
        dz = dialog.findChild(QCheckBox, "edit_support_dz")
        assert dz is not None
        assert dz.isChecked()
        dz.setChecked(False)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", accept_support_edit)
    support_position = window.canvas_2d.mapFromScene(QPointF(0, 15))
    QTest.mouseDClick(
        window.canvas_2d.viewport(), Qt.MouseButton.LeftButton, pos=support_position
    )

    assert window.script_editor.toPlainText().splitlines()[-1] == (
        "support N1 DX=true DY=false DZ=false RX=false RY=true RZ=false # keep"
    )
    support = compile_commands(window.script_editor.toPlainText())["supports"][0]
    assert support["DZ"] is False
    assert support["DY"] is False
    assert support["RX"] is False
    assert support["RZ"] is False
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
        "beam B1 H1 H2\n"
        "beam B2 V1 V2\n"
        "beam B3 L1 L2"
    )
    window.canvas_2d.set_model(model)

    fiber_lines = [
        item
        for item in window.canvas_2d.scene().items()
        if isinstance(item, QGraphicsLineItem)
        and item.pen().color().name() == "#747c85"
    ]
    beam_lines = [
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
    assert len(beam_lines) == 3
    assert len(axis_lines) == 2
    assert beam_lines[0].pen().widthF() > axis_lines[0].pen().widthF()
    assert all(
        fiber.pen().widthF() < beam_lines[0].pen().widthF() for fiber in fiber_lines
    )
    assert (
        beam_lines[0].pen().color().lightness()
        < axis_lines[0].pen().color().lightness()
    )
    horizontal_fibers = [
        item for item in fiber_lines if item.line().y1() == pytest.approx(7)
    ]
    vertical_fibers = [
        item for item in fiber_lines if item.line().x1() == pytest.approx(97)
    ]
    long_beam_fibers = [
        item for item in fiber_lines if item.line().y1() == pytest.approx(127)
    ]
    assert len(horizontal_fibers) == len(vertical_fibers) == 3
    assert len(long_beam_fibers) == 3
    assert sum(
        (item.line().x1() + item.line().x2()) / 2 for item in horizontal_fibers
    ) / 3 == pytest.approx(30)
    assert sum(
        (item.line().y1() + item.line().y2()) / 2 for item in vertical_fibers
    ) / 3 == pytest.approx(30)
    assert sum(
        (item.line().x1() + item.line().x2()) / 2 for item in long_beam_fibers
    ) / 3 == pytest.approx(120)
    assert max(item.line().x2() - item.line().x1() for item in long_beam_fibers) > (
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
