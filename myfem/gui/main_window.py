# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-24 22:30 CET: Copilot: Added double-click node coordinate editing
# 2026-11-24 22:40 CET: Copilot: Added undo toolbar action for script edits
# 2026-11-24 22:50 CET: Copilot: Added selectable and editable beams and supports
# 2026-11-24 23:05 CET: Copilot: Added prompted beam splitting for inserted nodes
# 2026-11-24 23:15 CET: Copilot: Added node context actions and concise script defaults
# 2026-11-24 23:24 CET: Copilot: Shortened node deletion menu label
# 2026-11-24 23:39 CET: Copilot: Displays date-formatted package versions
# 2026-11-24 23:47 CET: Copilot: Suggests timestamped model filenames
# 2026-11-24 23:51 CET: Copilot: Orders split confirmation as Yes then No
# 2026-11-25 00:01 CET: Copilot: Moves canvas instructions into the Help menu

"""Command-oriented MyFEM window for recording replayable model scripts."""

import shlex
import subprocess
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QUrl
from PySide6.QtGui import (
    QCloseEvent,
    QDesktopServices,
    QIcon,
    QKeySequence,
    QMouseEvent,
    QShortcut,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from myfem.gui.editor_2d import ModelCanvas2D
from myfem.pynite_export import generate_and_run
from myfem.script import (
    beams_at_point,
    compile_commands,
    delete_node_from_script,
    delete_support_from_script,
    split_beams_at_node,
    write_model,
)
from myfem.versioning import FORMAT_VERSION, format_package_version

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_URL = "https://github.com/JoKalliauer/MyFEM"
_GUI_INSTRUCTIONS = (
    "Enter nodes and beams in the x-z plane. Canvas clicks snap to 0.5 m.\n\n"
    "Left-click the Node or Beam toolbar icon, then click the canvas to create "
    "objects graphically. Right-click either icon to enter coordinates or "
    "beam endpoints in a dialog.\n\n"
    "Three gray dashes indicate the reference fiber (+local z). Click a node, "
    "beam, or support to select it; double-click to edit. Right-click a node "
    "for its context menu.\n\n"
    "Supports use their DX, DZ, and RY restraints. Changes are recorded in "
    "the .mfs script. Press Esc to return to Select mode."
)
_ICON_DIRECTORY = (
    _PROJECT_ROOT / "not_GPLv3" / "CC-BY-SA4.0" / "RFEM-6-Scaled-Sums-Envelope"
)


def _application_version() -> str:
    package_version = _distribution_version("myfem", FORMAT_VERSION)
    if package_version == FORMAT_VERSION:
        return FORMAT_VERSION
    return format_package_version(package_version)


def _distribution_version(distribution_name: str, fallback: str) -> str:
    try:
        return version(distribution_name)
    except PackageNotFoundError:
        return fallback


def _update_instructions() -> str:
    return (
        f"MyFEM version {_application_version()}\n\n"
        "Updates are not installed automatically. For a source checkout, "
        "save or commit your work, then run these commands from the "
        "repository root:\n\n"
        "    git status\n"
        "    git pull --ff-only\n"
        "    uv sync\n"
        "    uv run myfem\n\n"
        "Check the MyFEM GitHub page for available releases and updates:\n"
        f"{_PROJECT_URL}"
    )


def _about_html() -> str:
    return (
        f"<h3>MyFEM {_application_version()}</h3>"
        "<p>Maintainer and principal author: "
        '<a href="https://github.com/JoKalliauer">Johannes Kalliauer</a>.</p>'
        "<p>License: GNU GPLv3 "
        f'(<a href="{_PROJECT_URL}/blob/main/LICENSE">license</a>).</p>'
        "<h4>Solver</h4>"
        f"<p>PyNiteFEA {_distribution_version('PyNiteFEA', 'not installed')} "
        "was created by D. Craig Brinck, PE, SE. The upstream project is "
        'maintained by <a href="https://github.com/JWock82">Craig '
        "(@JWock82)</a>. It is licensed under MIT "
        '(<a href="https://github.com/JWock82/Pynite/blob/main/LICENSE">'
        "license</a>). See the "
        '<a href="https://github.com/JWock82/Pynite/graphs/contributors">'
        "contributor list</a>.</p>"
        "<h4>Artwork and toolbar icons</h4>"
        "<p><i>Screenshot von RFEM</i> by @ndre@s, Wikimedia Commons "
        "(CC BY-SA 3.0); and <i>RFEM-6-Scaled-Sums-Envelope</i> plus its "
        "adapted toolbar icons by @ndre@s, Wikimedia Commons (CC BY-SA 4.0). "
        "See the "
        '<a href="https://commons.wikimedia.org/wiki/File:Screenshot_von_RFEM.png">'
        "screenshot</a>, "
        '<a href="https://commons.wikimedia.org/wiki/File:RFEM-6-Scaled-Sums-Envelope.png">'
        "RFEM-6 illustration</a>, and the "
        '<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a>'
        " and "
        '<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>'
        " license terms.</p>"
        "<h4>AI disclosure</h4>"
        "<p>The majority of MyFEM's source code and documentation was generated "
        "by LLM-based AI, under human direction. Individual files declare their "
        "AI involvement in their headers.</p>"
        "<h4>Safety and liability</h4>"
        "<p>Structural analysis results must be independently checked by a "
        "qualified engineer. The software is provided without warranty, to "
        "the extent permitted by law.</p>"
    )


def _load_icon(filename: str) -> QIcon:
    icon_path = _ICON_DIRECTORY / filename
    if not icon_path.is_file():
        raise FileNotFoundError(f"Required GUI icon not found: {icon_path}")
    return QIcon(str(icon_path))


def _number_field(
    value: float = 0.0,
    minimum: float = -1_000_000_000_000,
    maximum: float = 1_000_000_000_000,
) -> QDoubleSpinBox:
    field = QDoubleSpinBox()
    field.setDecimals(6)
    field.setRange(minimum, maximum)
    field.setValue(value)
    return field


def _format_number(value: float) -> str:
    return format(value, ".15g")


def _script_token(value: str) -> str:
    return shlex.quote(value.strip())


def _split_script_comment(line: str) -> tuple[str, str]:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(line):
        if escaped:
            escaped = False
        elif character == "\\" and quote != "'":
            escaped = True
        elif quote is not None:
            if character == quote:
                quote = None
        elif character in ("'", '"'):
            quote = character
        elif character == "#":
            return line[:index], line[index:]
    return line, ""


def _record_ids(model: dict[str, object], collection: str) -> list[str]:
    records = model.get(collection)
    if not isinstance(records, list):
        raise TypeError(f"Model {collection} must be a list")
    identifiers = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise TypeError(f"Each model {collection} item must have a string id")
        identifiers.append(record["id"])
    return identifiers


def _next_identifier(prefix: str, identifiers: list[str]) -> str:
    existing = set(identifiers)
    number = 1
    while f"{prefix}{number}" in existing:
        number += 1
    return f"{prefix}{number}"


class MainWindow(QMainWindow):
    """Edit a MyFEM command log and generate its model JSON."""

    def __init__(self) -> None:
        super().__init__()
        self.current_script: Path | None = None
        self._new_model = True
        self._beam_start_node: str | None = None
        self.setWindowTitle("MyFEM command editor[*]")
        self.resize(900, 600)

        self.script_editor = QPlainTextEdit()
        self.script_editor.setPlaceholderText(
            "Recorded model commands will appear here."
        )
        self.script_editor.document().modificationChanged.connect(
            self.setWindowModified
        )
        self.script_editor.textChanged.connect(self._refresh_model_canvas)

        self.canvas_2d = ModelCanvas2D()
        self.canvas_2d.node_position_clicked.connect(self._add_canvas_node)
        self.canvas_2d.node_selected.connect(self._canvas_node_selected)
        self.canvas_2d.object_selected.connect(self._canvas_object_selected)
        self.canvas_2d.object_double_clicked.connect(self._edit_canvas_object)
        self.canvas_2d.node_context_requested.connect(self._show_node_context_menu)
        self.canvas_2d.message_requested.connect(
            lambda message: self.statusBar().showMessage(message, 5000)
        )
        self._right_click_dialog_modes: dict[QObject, Literal["node", "beam"]] = {}

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter a command, e.g. node N1 x=0 z=0")
        self.add_button = QPushButton("Add command")
        self.add_button.clicked.connect(self._add_command)
        self.command_input.returnPressed.connect(self._add_command)

        command_row = QHBoxLayout()
        command_row.addWidget(self.command_input)
        command_row.addWidget(self.add_button)

        layout = QVBoxLayout()
        model_splitter = QSplitter(Qt.Orientation.Horizontal)
        model_splitter.addWidget(self.canvas_2d)
        model_splitter.addWidget(self.script_editor)
        model_splitter.setStretchFactor(0, 3)
        model_splitter.setStretchFactor(1, 2)
        layout.addWidget(model_splitter, 1)
        layout.addLayout(command_row)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self._set_canvas_mode("select")
        self._refresh_model_canvas()
        self._create_menu()
        self._create_toolbar()
        self.select_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.select_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.select_shortcut.activated.connect(lambda: self._set_canvas_mode("select"))

    def _install_right_click_dialog(
        self, widget: QWidget | None, mode: Literal["node", "beam"]
    ) -> None:
        if widget is None:
            raise RuntimeError(f"Could not find the {mode} input control")
        self._right_click_dialog_modes[widget] = mode
        widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        mode = self._right_click_dialog_modes.get(watched)
        if (
            mode is not None
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(event, QMouseEvent)
            and event.button() == Qt.MouseButton.RightButton
        ):
            if mode == "node":
                self.add_node()
            else:
                self.add_beam()
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def _set_canvas_mode(self, mode: Literal["select", "node", "beam"]) -> None:
        self._beam_start_node = None
        self.canvas_2d.set_pending_node(None)
        self.canvas_2d.set_mode(mode)
        messages = {
            "select": "Select mode: click a node, beam, or support; double-click to edit.",
            "node": "Node mode: click the canvas to add a node (snap: 0.5 m).",
            "beam": "Beam mode: click two existing nodes in order.",
        }
        self.statusBar().showMessage(messages[mode])

    def _refresh_model_canvas(self) -> None:
        try:
            model = compile_commands(self.script_editor.toPlainText())
        except (TypeError, ValueError) as error:
            self._beam_start_node = None
            self.canvas_2d.set_pending_node(None)
            self.canvas_2d.set_model(None)
            if self.script_editor.toPlainText().strip():
                self.statusBar().showMessage(f"2D view unavailable: {error}", 5000)
            return

        node_ids = _record_ids(model, "nodes")
        if self._beam_start_node not in node_ids:
            self._beam_start_node = None
            self.canvas_2d.set_pending_node(None)
        self.canvas_2d.set_model(model)

    def _add_canvas_node(self, x: float, z: float) -> None:
        try:
            model = compile_commands(self.script_editor.toPlainText())
        except (TypeError, ValueError) as error:
            self.statusBar().showMessage(f"Cannot add node: {error}", 5000)
            return

        node_id = _next_identifier("N", _record_ids(model, "nodes"))
        command = f"node {node_id} x={_format_number(x)} z={_format_number(z)}"
        self._record_new_node(node_id, x, z, command)

    def _record_new_node(self, node_id: str, x: float, z: float, command: str) -> None:
        source = self.script_editor.toPlainText()
        separator = "" if not source or source.endswith("\n") else "\n"
        try:
            compile_commands(f"{source}{separator}{command}")
            beam_ids = beams_at_point(source, x, z)
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Could not add node", str(error))
            return

        if not beam_ids:
            self._append_model_command(command, "Could not add node")
            return

        beam_label = "beam" if len(beam_ids) == 1 else "beams"
        beam_list = ", ".join(beam_ids)
        question = (
            f"Node {node_id} lies on {beam_label} {beam_list}. "
            f"Split {beam_label} at this node?"
        )
        if not self._confirm_beam_split(question):
            self._append_model_command(command, "Could not add node")
            return

        try:
            candidate = split_beams_at_node(source, command, beam_ids)
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Could not split beam", str(error))
            return
        self._replace_script_text(candidate)
        self.statusBar().showMessage(
            f"Node {node_id} added; split {beam_label} {beam_list}.", 5000
        )

    def _confirm_beam_split(self, question: str) -> bool:
        dialog = QDialog(self)
        dialog.setObjectName("split_beam_dialog")
        dialog.setWindowTitle("Split beam?")
        layout = QVBoxLayout(dialog)
        message = QLabel(question, dialog)
        message.setObjectName("split_beam_question")
        layout.addWidget(message)

        buttons = QHBoxLayout()
        buttons.setObjectName("split_beam_button_row")
        buttons.addStretch()
        yes_button = QPushButton("Yes", dialog)
        yes_button.setObjectName("split_beam_yes")
        yes_button.setDefault(True)
        no_button = QPushButton("No", dialog)
        no_button.setObjectName("split_beam_no")
        buttons.addWidget(yes_button)
        buttons.addWidget(no_button)
        layout.addLayout(buttons)
        yes_button.clicked.connect(dialog.accept)
        no_button.clicked.connect(dialog.reject)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def _replace_script_text(self, text: str) -> None:
        cursor = QTextCursor(self.script_editor.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.beginEditBlock()
        cursor.insertText(text)
        cursor.endEditBlock()
        self.script_editor.setTextCursor(cursor)

    def _canvas_node_selected(self, node_id: str) -> None:
        if self.canvas_2d.mode != "beam":
            return

        if self._beam_start_node is None:
            self._beam_start_node = node_id
            self.canvas_2d.set_pending_node(node_id)
            self.statusBar().showMessage(
                f"Beam start node {node_id} selected; click the end node."
            )
            return

        start_node = self._beam_start_node
        if start_node == node_id:
            self.statusBar().showMessage(
                "Choose a different node for the beam end.", 5000
            )
            return

        try:
            model = compile_commands(self.script_editor.toPlainText())
        except (TypeError, ValueError) as error:
            self.statusBar().showMessage(f"Cannot add beam: {error}", 5000)
            return

        beam_id = _next_identifier("B", _record_ids(model, "beams"))
        command = f"beam {beam_id} {start_node} {node_id}"
        if self._append_model_command(command, "Could not add beam"):
            self._beam_start_node = None
            self.canvas_2d.set_pending_node(None)

    def _canvas_object_selected(self, kind: str, identifier: str) -> None:
        if not kind:
            self.statusBar().showMessage("Selection cleared.", 3000)
        elif kind == "support":
            self.statusBar().showMessage(
                f"Selected support at node {identifier}.", 3000
            )
        else:
            self.statusBar().showMessage(f"Selected {kind} {identifier}.", 3000)

    def _edit_canvas_object(self, kind: str, identifier: str) -> None:
        if kind == "node":
            self.edit_node(identifier)
        elif kind == "beam":
            self.edit_beam(identifier)
        elif kind == "support":
            self.edit_support(identifier)
        else:
            raise ValueError(f"Unknown canvas object type {kind!r}")

    def _show_node_context_menu(self, node_id: str, position: QPoint) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        supports = model.get("supports")
        if not isinstance(supports, list):
            raise TypeError("Model supports must be a list")
        has_support = any(
            isinstance(support, dict) and support.get("node") == node_id
            for support in supports
        )

        menu = QMenu(self)
        delete_action = menu.addAction("Delete node")
        delete_action.setObjectName("delete_node_context_action")
        edit_action = menu.addAction("Edit node")
        edit_action.setObjectName("edit_node_context_action")
        menu.addSeparator()
        support_action = menu.addAction(
            "Edit support" if has_support else "Add support"
        )
        support_action.setObjectName("support_context_action")
        delete_action.triggered.connect(
            lambda _checked=False: self.delete_node(node_id)
        )
        edit_action.triggered.connect(lambda _checked=False: self.edit_node(node_id))
        if has_support:
            support_action.triggered.connect(
                lambda _checked=False: self.edit_support(node_id)
            )
        else:
            support_action.triggered.connect(
                lambda _checked=False: self.add_support(node_id)
            )
        self._execute_context_menu(menu, position)

    def _execute_context_menu(self, menu: QMenu, position: QPoint) -> None:
        menu.exec(position)

    def delete_node(self, node_id: str) -> None:
        try:
            model = compile_commands(self.script_editor.toPlainText())
            beams = model.get("beams")
            loads = model.get("loads")
            supports = model.get("supports")
            if not isinstance(beams, list) or not isinstance(loads, list):
                raise TypeError("Model beams and loads must be lists")
            if not isinstance(supports, list):
                raise TypeError("Model supports must be a list")
            deleted_beams = {
                beam["id"]
                for beam in beams
                if isinstance(beam, dict)
                and isinstance(beam.get("id"), str)
                and node_id in (beam.get("node_start"), beam.get("node_end"))
            }
            deleted_load_count = sum(
                1
                for load in loads
                if isinstance(load, dict) and load.get("beam") in deleted_beams
            )
            has_support = any(
                isinstance(support, dict) and support.get("node") == node_id
                for support in supports
            )
            updated_script = delete_node_from_script(
                self.script_editor.toPlainText(), node_id
            )
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Could not delete node", str(error))
            return

        self._replace_script_text(updated_script)
        deleted_objects = [f"Deleted node {node_id}"]
        if deleted_beams:
            deleted_objects.append(
                f"{len(deleted_beams)} connected beam"
                f"{'s' if len(deleted_beams) != 1 else ''}"
            )
        if has_support:
            deleted_objects.append("its support")
        if deleted_load_count:
            deleted_objects.append(
                f"{deleted_load_count} associated distributed load"
                f"{'s' if deleted_load_count != 1 else ''}"
            )
        self.statusBar().showMessage(", ".join(deleted_objects) + ".", 5000)

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        new_action = file_menu.addAction("&New model")
        new_action.triggered.connect(self.new_script)
        open_action = file_menu.addAction("&Open script...")
        open_action.triggered.connect(lambda: self.open_script())
        save_action = file_menu.addAction("&Save script")
        save_action.triggered.connect(lambda: self.save_script())
        save_as_action = file_menu.addAction("Save script &as...")
        save_as_action.triggered.connect(lambda: self.save_script_as())
        calculate_action = file_menu.addAction("&Calculate")
        calculate_action.triggered.connect(self.calculate)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

        self.help_menu = self.menuBar().addMenu("&Help")
        self.instructions_action = self.help_menu.addAction("&GUI instructions...")
        self.instructions_action.triggered.connect(self.show_gui_instructions)
        self.update_action = self.help_menu.addAction("&Update instructions...")
        self.update_action.triggered.connect(self.show_update_information)
        self.about_action = self.help_menu.addAction("&About MyFEM")
        self.about_action.triggered.connect(self.show_about)
        self.help_menu.addSeparator()
        self.project_action = self.help_menu.addAction("MyFEM on &GitHub")
        self.project_action.triggered.connect(self.open_project_page)

    def _create_toolbar(self) -> None:
        self.file_toolbar = QToolBar("File actions", self)
        self.file_toolbar.setObjectName("file_toolbar")
        self.file_toolbar.setMovable(False)
        self.file_toolbar.setFloatable(False)
        self.file_toolbar.setIconSize(QSize(25, 25))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.file_toolbar)

        self.new_action = self.file_toolbar.addAction(
            _load_icon("newFile_icon_RFEM6.png"), "New"
        )
        self.new_action.setToolTip("New model; Save creates .mfs and .json files")
        self.new_action.triggered.connect(self.new_script)

        self.open_action = self.file_toolbar.addAction(
            _load_icon("open_icon_RFEM6.png"), "Open script"
        )
        self.open_action.setToolTip("Open a MyFEM .mfs script")
        self.open_action.triggered.connect(self.open_script)

        self.save_action = self.file_toolbar.addAction(
            _load_icon("save_icon_RFEM6.png"), "Save script"
        )
        self.save_action.setToolTip("Save the .mfs script and matching .json model")
        self.save_action.triggered.connect(self.save_script)

        self.undo_action = self.file_toolbar.addAction(
            _load_icon("undo_icon_RFEM6.png"), "Undo"
        )
        self.undo_action.setToolTip("Undo the last script edit")
        self.undo_action.triggered.connect(self.script_editor.undo)
        self.script_editor.undoAvailable.connect(self.undo_action.setEnabled)
        self.undo_action.setEnabled(self.script_editor.document().isUndoAvailable())

        self.add_node_action = self.file_toolbar.addAction(
            _load_icon("newNode_icon_RFEM6.png"), "Add node"
        )
        self.add_node_action.setToolTip(
            "Left-click: create a node graphically; right-click: enter coordinates"
        )
        self.add_node_action.triggered.connect(lambda: self._set_canvas_mode("node"))
        self._install_right_click_dialog(
            self.file_toolbar.widgetForAction(self.add_node_action), "node"
        )

        self.add_beam_action = self.file_toolbar.addAction(
            _load_icon("newBeam_icon_RFEM6.png"), "Add beam"
        )
        self.add_beam_action.setToolTip(
            "Left-click: create a beam graphically; right-click: enter endpoints"
        )
        self.add_beam_action.triggered.connect(lambda: self._set_canvas_mode("beam"))
        self._install_right_click_dialog(
            self.file_toolbar.widgetForAction(self.add_beam_action), "beam"
        )

        self.add_support_action = self.file_toolbar.addAction(
            _load_icon("Support_icon_RFEM6.png"), "Add support"
        )
        self.add_support_action.setToolTip("Add a support at a node")
        self.add_support_action.triggered.connect(lambda: self.add_support())

        self.add_load_action = self.file_toolbar.addAction(
            _load_icon("NodeLoad_icon_RFEM6.png"), "Add distributed load"
        )
        self.add_load_action.setToolTip("Add a distributed beam load")
        self.add_load_action.triggered.connect(self.add_distributed_load)

        self.calculate_action = self.file_toolbar.addAction(
            _load_icon("calculate_icon_RFEM6.png"), "Calculate"
        )
        self.calculate_action.setToolTip(
            "Save .mfs and .json, generate .py, run PyNite, and write .out"
        )
        self.calculate_action.triggered.connect(self.calculate)

    def show_about(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("About MyFEM")
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setHtml(_about_html())
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def show_gui_instructions(self) -> None:
        QMessageBox.information(self, "GUI instructions", _GUI_INSTRUCTIONS)

    def show_update_information(self) -> None:
        QMessageBox.information(
            self,
            "MyFEM update instructions",
            _update_instructions(),
        )

    def open_project_page(self) -> None:
        if not QDesktopServices.openUrl(QUrl(_PROJECT_URL)):
            QMessageBox.warning(
                self,
                "Could not open MyFEM on GitHub",
                f"Open this URL in a browser:\n{_PROJECT_URL}",
            )

    def _model_for_dialog(self) -> dict[str, object] | None:
        try:
            return compile_commands(self.script_editor.toPlainText())
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Cannot add model object", str(error))
            return None

    def _append_model_command(self, command: str, title: str) -> bool:
        existing = self.script_editor.toPlainText()
        trimmed = existing.rstrip()
        insertion = f"\n{command}" if trimmed else command
        candidate = f"{trimmed}{insertion}"
        try:
            compile_commands(candidate)
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, title, str(error))
            return False

        cursor = QTextCursor(self.script_editor.document())
        cursor.setPosition(len(trimmed))
        cursor.movePosition(
            QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor
        )
        cursor.beginEditBlock()
        cursor.insertText(insertion)
        cursor.endEditBlock()
        self.script_editor.setTextCursor(cursor)
        self.statusBar().showMessage("Command recorded in the script.", 3000)
        return True

    def edit_node(self, node_id: str) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        nodes = model.get("nodes")
        if not isinstance(nodes, list):
            raise TypeError("Model nodes must be a list")
        node = next(
            (
                record
                for record in nodes
                if isinstance(record, dict) and record.get("id") == node_id
            ),
            None,
        )
        if node is None:
            QMessageBox.warning(self, "Cannot edit node", f"Node {node_id!r} not found")
            return
        x = node.get("x")
        z = node.get("z")
        if (
            isinstance(x, bool)
            or not isinstance(x, (int, float))
            or isinstance(z, bool)
            or not isinstance(z, (int, float))
        ):
            raise TypeError(f"Node {node_id!r} must have numeric x and z coordinates")

        x_field = _number_field(float(x))
        x_field.setObjectName("edit_node_x")
        z_field = _number_field(float(z))
        z_field.setObjectName("edit_node_z")
        displayed_x = x_field.value()
        displayed_z = z_field.value()
        y_field = _number_field()
        y_field.setObjectName("edit_node_y")
        y_field.setReadOnly(True)
        y_field.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        dialog = QDialog(self)
        dialog.setObjectName("edit_node_dialog")
        dialog.setWindowTitle(f"Edit node {node_id}")
        form = QFormLayout(dialog)
        form.addRow("Node", QLabel(node_id))
        form.addRow("X", x_field)
        form.addRow("Y (fixed at 0 in 2D)", y_field)
        form.addRow("Z", z_field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        updated_x = float(x) if x_field.value() == displayed_x else x_field.value()
        updated_z = float(z) if z_field.value() == displayed_z else z_field.value()
        self._replace_node_command(node_id, updated_x, updated_z)

    def _replace_node_command(self, node_id: str, x: float, z: float) -> None:
        command = (
            f"node {_script_token(node_id)} x={_format_number(x)} z={_format_number(z)}"
        )
        self._replace_model_command("node", node_id, command, "node")

    def _replace_model_command(
        self, command_name: str, identifier: str, replacement: str, label: str
    ) -> None:
        lines = self.script_editor.toPlainText().split("\n")
        matched_line: int | None = None
        for index, line in enumerate(lines):
            source, comment = _split_script_comment(line)
            try:
                tokens = shlex.split(source)
            except ValueError as error:
                QMessageBox.warning(self, f"Could not edit {label}", str(error))
                return
            if (
                len(tokens) >= 2
                and tokens[0] == command_name
                and tokens[1] == identifier
            ):
                indentation = source[: len(source) - len(source.lstrip())]
                comment_suffix = f" {comment.lstrip()}" if comment else ""
                lines[index] = f"{indentation}{replacement}{comment_suffix}"
                matched_line = index
                break
        if matched_line is None:
            QMessageBox.warning(
                self,
                f"Could not edit {label}",
                f"No command found for {label} {identifier!r}",
            )
            return

        candidate = "\n".join(lines)
        if candidate == self.script_editor.toPlainText():
            self.statusBar().showMessage(
                f"{label.title()} {identifier} unchanged.", 3000
            )
            return
        try:
            compile_commands(candidate)
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, f"Could not edit {label}", str(error))
            return

        block = self.script_editor.document().findBlockByNumber(matched_line)
        if not block.isValid():
            raise RuntimeError(
                f"Could not locate the script command for {label} {identifier!r}"
            )
        cursor = QTextCursor(self.script_editor.document())
        cursor.setPosition(block.position())
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor
        )
        cursor.beginEditBlock()
        cursor.insertText(lines[matched_line])
        cursor.endEditBlock()
        self.script_editor.setTextCursor(cursor)
        self.statusBar().showMessage(f"{label.title()} {identifier} updated.", 3000)

    def edit_beam(self, beam_id: str) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        beams = model.get("beams")
        if not isinstance(beams, list):
            raise TypeError("Model beams must be a list")
        beam = next(
            (
                record
                for record in beams
                if isinstance(record, dict) and record.get("id") == beam_id
            ),
            None,
        )
        if beam is None:
            QMessageBox.warning(self, "Cannot edit beam", f"Beam {beam_id!r} not found")
            return

        node_ids = _record_ids(model, "nodes")
        node_start = beam.get("node_start")
        node_end = beam.get("node_end")
        material_id = beam.get("material")
        section_id = beam.get("section")
        if not (
            isinstance(node_start, str)
            and isinstance(node_end, str)
            and isinstance(material_id, str)
            and isinstance(section_id, str)
        ):
            raise TypeError(
                f"Beam {beam_id!r} must define endpoints, material, and section"
            )

        start_node = QComboBox()
        start_node.setObjectName("edit_beam_start_node")
        start_node.addItems(node_ids)
        start_node.setCurrentText(node_start)
        end_node = QComboBox()
        end_node.setObjectName("edit_beam_end_node")
        end_node.addItems(node_ids)
        end_node.setCurrentText(node_end)

        material_options = [
            "default",
            *(
                identifier
                for identifier in _record_ids(model, "materials")
                if identifier != "default"
            ),
        ]
        material = QComboBox()
        material.setObjectName("edit_beam_material")
        material.addItems(material_options)
        current_material = (
            "default" if beam.get("material_was_default") is True else material_id
        )
        if current_material not in material_options:
            raise ValueError(
                f"Unknown material {current_material!r} on beam {beam_id!r}"
            )
        material.setCurrentText(current_material)

        section_options = [
            "default",
            *(
                identifier
                for identifier in _record_ids(model, "sections")
                if identifier != "default"
            ),
        ]
        section = QComboBox()
        section.setObjectName("edit_beam_section")
        section.addItems(section_options)
        current_section = (
            "default" if beam.get("section_was_default") is True else section_id
        )
        if current_section not in section_options:
            raise ValueError(f"Unknown section {current_section!r} on beam {beam_id!r}")
        section.setCurrentText(current_section)

        dialog = QDialog(self)
        dialog.setObjectName("edit_beam_dialog")
        dialog.setWindowTitle(f"Edit beam {beam_id}")
        form = QFormLayout(dialog)
        form.addRow("Beam", QLabel(beam_id))
        form.addRow("Start node", start_node)
        form.addRow("End node", end_node)
        form.addRow("Material", material)
        form.addRow("Section", section)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        command = (
            f"beam {_script_token(beam_id)} "
            f"{_script_token(start_node.currentText())} "
            f"{_script_token(end_node.currentText())}"
        )
        if material.currentText() != "default":
            command += f" material={_script_token(material.currentText())}"
        if section.currentText() != "default":
            command += f" section={_script_token(section.currentText())}"
        self._replace_model_command("beam", beam_id, command, "beam")

    def edit_support(self, node_id: str) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        supports = model.get("supports")
        if not isinstance(supports, list):
            raise TypeError("Model supports must be a list")
        support = next(
            (
                record
                for record in supports
                if isinstance(record, dict) and record.get("node") == node_id
            ),
            None,
        )
        if support is None:
            QMessageBox.warning(
                self, "Cannot edit support", f"No support found at node {node_id!r}"
            )
            return

        dx_state = support.get("DX")
        dy_state = support.get("DY")
        dz_state = support.get("DZ")
        rx_state = support.get("RX")
        ry_state = support.get("RY")
        rz_state = support.get("RZ")
        if not (
            isinstance(dx_state, bool)
            and isinstance(dy_state, bool)
            and isinstance(dz_state, bool)
            and isinstance(rx_state, bool)
            and isinstance(ry_state, bool)
            and isinstance(rz_state, bool)
        ):
            raise TypeError(f"Support at node {node_id!r} must define six Boolean DOFs")
        dx = QCheckBox()
        dx.setObjectName("edit_support_dx")
        dx.setChecked(dx_state)
        dz = QCheckBox()
        dz.setObjectName("edit_support_dz")
        dz.setChecked(dz_state)
        ry = QCheckBox()
        ry.setObjectName("edit_support_ry")
        ry.setChecked(ry_state)

        dialog = QDialog(self)
        dialog.setObjectName("edit_support_dialog")
        dialog.setWindowTitle(f"Edit support at {node_id}")
        form = QFormLayout(dialog)
        form.addRow("Node", QLabel(node_id))
        form.addRow("DX", dx)
        form.addRow("DZ", dz)
        form.addRow("RY", ry)
        form.addRow(QLabel("DY, RX, and RZ are preserved from the script."))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        editable_dofs = {
            "DX": dx.isChecked(),
            "DY": dy_state,
            "DZ": dz.isChecked(),
            "RX": rx_state,
            "RY": ry.isChecked(),
            "RZ": rz_state,
        }
        if not any(editable_dofs[key] for key in ("DX", "DZ", "RY")):
            try:
                updated_script = delete_support_from_script(
                    self.script_editor.toPlainText(), node_id
                )
            except (TypeError, ValueError) as error:
                QMessageBox.warning(self, "Could not remove support", str(error))
                return
            self._replace_script_text(updated_script)
            self.statusBar().showMessage(
                f"Support at node {node_id} removed; all 2D restraints are free.",
                5000,
            )
            return

        options = " ".join(
            f"{key}={str(value).lower()}"
            for key, value in editable_dofs.items()
            if key in ("DX", "DZ", "RY") or not value
        )
        command = f"support {_script_token(node_id)} {options}"
        self._replace_model_command("support", node_id, command, "support")

    def add_node(self) -> None:
        model = self._model_for_dialog()
        if model is None:
            return

        node_name = QLineEdit(_next_identifier("N", _record_ids(model, "nodes")))
        node_name.setObjectName("node_name")
        x_field = _number_field()
        x_field.setObjectName("node_x")
        y_field = _number_field()
        y_field.setObjectName("node_y")
        y_field.setReadOnly(True)
        y_field.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        z_field = _number_field()
        z_field.setObjectName("node_z")

        dialog = QDialog(self)
        dialog.setObjectName("add_node_dialog")
        dialog.setWindowTitle("Add node")
        form = QFormLayout(dialog)
        form.addRow("Node name", node_name)
        form.addRow("X", x_field)
        form.addRow("Y (fixed at 0 in 2D)", y_field)
        form.addRow("Z", z_field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        node_id = node_name.text().strip()
        command = (
            f"node {_script_token(node_id)} "
            f"x={_format_number(x_field.value())} z={_format_number(z_field.value())}"
        )
        self._record_new_node(node_id, x_field.value(), z_field.value(), command)

    def add_beam(self) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        node_ids = _record_ids(model, "nodes")
        if len(node_ids) < 2:
            QMessageBox.information(
                self, "Add beam", "Create at least two nodes first."
            )
            return

        beam_name = QLineEdit(_next_identifier("B", _record_ids(model, "beams")))
        beam_name.setObjectName("beam_name")
        start_node = QComboBox()
        start_node.setObjectName("beam_start_node")
        start_node.addItems(node_ids)
        end_node = QComboBox()
        end_node.setObjectName("beam_end_node")
        end_node.addItems(node_ids)
        end_node.setCurrentIndex(1)

        dialog = QDialog(self)
        dialog.setObjectName("add_beam_dialog")
        dialog.setWindowTitle("Add beam")
        form = QFormLayout(dialog)
        form.addRow("Beam name", beam_name)
        form.addRow("Start node", start_node)
        form.addRow("End node", end_node)
        form.addRow(QLabel("Material and section: default"))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        command = (
            f"beam {_script_token(beam_name.text())} "
            f"{_script_token(start_node.currentText())} "
            f"{_script_token(end_node.currentText())}"
        )
        self._append_model_command(command, "Could not add beam")

    def add_support(self, node_id: str | None = None) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        node_ids = _record_ids(model, "nodes")
        if not node_ids:
            QMessageBox.information(self, "Add support", "Create a node first.")
            return

        node = QComboBox()
        node.setObjectName("support_node")
        node.addItems(node_ids)
        if node_id is not None:
            node.setCurrentText(node_id)
        dx = QCheckBox()
        dx.setObjectName("support_dx")
        dx.setChecked(True)
        dz = QCheckBox()
        dz.setObjectName("support_dz")
        dz.setChecked(True)
        ry = QCheckBox()
        ry.setObjectName("support_ry")

        dialog = QDialog(self)
        dialog.setObjectName("add_support_dialog")
        dialog.setWindowTitle("Add support")
        form = QFormLayout(dialog)
        form.addRow("Node", node)
        form.addRow("DX", dx)
        form.addRow("DZ", dz)
        form.addRow("RY", ry)
        form.addRow(QLabel("In the 2D setup, DY, RX, and RZ are fixed to true."))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if not (dx.isChecked() or dz.isChecked() or ry.isChecked()):
            self.statusBar().showMessage(
                "No support added because all 2D restraints are free.", 5000
            )
            return

        command = (
            f"support {_script_token(node.currentText())} "
            f"DX={str(dx.isChecked()).lower()} "
            f"DZ={str(dz.isChecked()).lower()} RY={str(ry.isChecked()).lower()}"
        )
        self._append_model_command(command, "Could not add support")

    def add_distributed_load(self) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        beam_ids = _record_ids(model, "beams")
        if not beam_ids:
            QMessageBox.information(
                self, "Add distributed load", "Create a beam first."
            )
            return

        beams = model.get("beams")
        if not isinstance(beams, list):
            raise TypeError("Model beams must be a list")

        def beam_length(identifier: str) -> float:
            for record in beams:
                if (
                    isinstance(record, dict)
                    and record.get("id") == identifier
                    and isinstance(record.get("length"), (float, int))
                    and not isinstance(record.get("length"), bool)
                ):
                    return float(record["length"])
            raise ValueError(f"Could not determine the length of beam {identifier!r}")

        beam = QComboBox()
        beam.setObjectName("load_beam")
        beam.addItems(beam_ids)
        direction = QComboBox()
        direction.setObjectName("load_direction")
        direction.addItems(("FZ", "FX"))
        value_start = _number_field(10_000)
        value_start.setObjectName("load_value_start")
        value_end = _number_field(10_000)
        value_end.setObjectName("load_value_end")
        position_start = _number_field(0, minimum=0)
        position_start.setObjectName("load_position_start")
        initial_length = beam_length(beam.currentText())
        position_end = _number_field(initial_length, minimum=0)
        position_end.setObjectName("load_position_end")

        def update_beam_length(identifier: str) -> None:
            length = beam_length(identifier)
            position_start.setMaximum(length)
            position_end.setMaximum(length)
            position_end.setValue(length)

        beam.currentTextChanged.connect(update_beam_length)

        dialog = QDialog(self)
        dialog.setObjectName("add_distributed_load_dialog")
        dialog.setWindowTitle("Add distributed load")
        form = QFormLayout(dialog)
        form.addRow("Beam", beam)
        form.addRow("Direction", direction)
        form.addRow("Start value (N/m)", value_start)
        form.addRow("End value (N/m)", value_end)
        form.addRow("Start position (m)", position_start)
        form.addRow("End position (m)", position_end)
        form.addRow(QLabel("Load case: default"))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        command = (
            f"load distributed {_script_token(beam.currentText())} "
            f"direction={direction.currentText()} "
            f"value_start={_format_number(value_start.value())} "
            f"value_end={_format_number(value_end.value())} "
            f"position_start={_format_number(position_start.value())} "
            f"position_end={_format_number(position_end.value())} case=default"
        )
        self._append_model_command(command, "Could not add distributed load")

    def new_script(self) -> None:
        if not self._confirm_discard():
            return
        self.script_editor.clear()
        self.command_input.clear()
        self.script_editor.document().setModified(False)
        self.current_script = None
        self._new_model = True
        self.statusBar().showMessage(
            "New model. Save it to create .mfs and .json files.", 5000
        )

    def _add_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            return

        if self._append_model_command(command, "Invalid command"):
            self.command_input.clear()

    def open_script(self) -> None:
        if not self._confirm_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open MyFEM script", "", "MyFEM scripts (*.mfs);;All files (*)"
        )
        if not filename:
            return
        path = Path(filename)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            QMessageBox.critical(self, "Could not open script", str(error))
            return

        self.script_editor.setPlainText(text)
        self.script_editor.document().setModified(False)
        self.current_script = path
        self._new_model = False
        self.statusBar().showMessage(f"Opened {path}", 3000)

    def save_script(self) -> bool:
        if self.current_script is None:
            return self.save_script_as()
        return self._save_to(self.current_script)

    def save_script_as(self) -> bool:
        suggested_path = self.current_script or Path(
            datetime.now().astimezone().strftime("MyFEM-Model-%Y-%m-%d_%H_%M.mfs")
        )
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save MyFEM script",
            str(suggested_path),
            "MyFEM scripts (*.mfs);;All files (*)",
        )
        if not filename:
            return False
        path = Path(filename)
        if path.suffix.lower() != ".mfs":
            path = path.with_suffix(".mfs")
        return self._save_to(path)

    def _save_to(self, path: Path) -> bool:
        text = self.script_editor.toPlainText()
        try:
            compile_commands(text, source_name=str(path))
            if self._new_model:
                text = self._new_script_source(text)
                compile_commands(text, source_name=str(path))
        except (TypeError, ValueError) as error:
            QMessageBox.critical(self, "Could not save model", str(error))
            return False

        try:
            path.write_text(text + "\n", encoding="utf-8")
        except OSError as error:
            QMessageBox.critical(
                self, "Could not save model", f"Could not save {path}:\n{error}"
            )
            return False

        self.current_script = path
        if self._new_model:
            self._replace_script_text(text)
            self._new_model = False
        self.script_editor.document().setModified(False)
        json_path = path.with_suffix(".json")
        try:
            write_model(path, json_path)
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(
                self,
                "Could not save JSON model",
                f"The script was saved to {path}, but {json_path} could not "
                f"be generated:\n{error}",
            )
            return False

        self.statusBar().showMessage(f"Saved {path} and {json_path}", 3000)
        return True

    def _new_script_source(self, body: str) -> str:
        now = datetime.now().astimezone()
        body_lines = [
            line
            for line in body.splitlines()
            if not (tokens := shlex.split(line, comments=True)) or tokens[0] != "model"
        ]
        version_line = (
            f"# Created with MyFEM GUI version {_application_version()} as of "
            f"{now.date().isoformat()}; format_version={FORMAT_VERSION}"
        )
        return "\n".join(
            (
                version_line,
                f"# Created: {now.isoformat(timespec='seconds')}",
                "model 2D xz x=right z=down",
                *body_lines,
            )
        )

    def calculate(self) -> None:
        if not self.save_script() or self.current_script is None:
            return

        script_path = self.current_script
        model_path = script_path.with_suffix(".json")
        python_path = script_path.with_suffix(".py")
        output_path = script_path.with_suffix(".out")
        self.statusBar().showMessage("Calculating with PyNite...")
        try:
            generate_and_run(model_path, python_path, output_path)
        except (
            OSError,
            TypeError,
            ValueError,
            subprocess.CalledProcessError,
        ) as error:
            QMessageBox.critical(self, "Calculation failed", str(error))
            return
        self.statusBar().showMessage(
            f"Calculation complete. Results saved to {output_path}", 5000
        )

    def _confirm_discard(self) -> bool:
        if not self.script_editor.document().isModified():
            return True
        answer = QMessageBox.question(
            self,
            "Unsaved script",
            "Save changes to the current script?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_script()
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
