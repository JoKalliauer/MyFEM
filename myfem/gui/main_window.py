# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:45 CET: Copilot: Added command-script editor and JSON export
# 2026-11-22 19:40 CET: Copilot: Added Calculate action and .out results
# 2026-11-22 21:20 CET: Copilot: Added file icons and paired MFS/JSON saving
# 2026-11-23 19:30 CET: Copilot: Matched toolbar icon names to available assets
# 2026-11-23 19:32 CET: Copilot: Moved file actions into a top toolbar
# 2026-11-23 19:37 CET: Copilot: Added help, license, version, and update information
# 2026-11-23 20:45 CET: Copilot: Separated safety notice in About dialog
# 2026-11-23 20:50 CET: Copilot: Disclosed project-wide LLM contribution in About
# 2026-11-23 21:17 CET: Copilot: Added node, member, support, and load entry tools
# 2026-11-23 23:35 CET: Copilot: Added 2D geometry, support, and fiber rendering

"""Command-oriented MyFEM window for recording replayable model scripts."""

import shlex
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QButtonGroup,
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
from myfem.script import compile_commands, write_model

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_URL = "https://github.com/JoKalliauer/MyFEM"
_ICON_DIRECTORY = (
    _PROJECT_ROOT / "not_GPLv3" / "CC-BY-SA4.0" / "RFEM-6-Scaled-Sums-Envelope"
)


def _application_version() -> str:
    return _distribution_version("myfem", "development")


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
        self._member_start_node: str | None = None
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
        self.canvas_2d.message_requested.connect(
            lambda message: self.statusBar().showMessage(message, 5000)
        )

        tool_row = QHBoxLayout()
        self.input_tool_group = QButtonGroup(self)
        self.input_tool_group.setExclusive(True)
        self.select_tool_button = self._create_input_tool(
            "Select", "select_tool_button", "select", tool_row
        )
        self.node_tool_button = self._create_input_tool(
            "Node", "node_tool_button", "node", tool_row
        )
        self.member_tool_button = self._create_input_tool(
            "Member", "member_tool_button", "member", tool_row
        )
        tool_row.addStretch(1)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText(
            "Enter a command, e.g. node N1 x=0 y=0 z=0"
        )
        self.add_button = QPushButton("Add command")
        self.add_button.clicked.connect(self._add_command)
        self.command_input.returnPressed.connect(self._add_command)

        command_row = QHBoxLayout()
        command_row.addWidget(self.command_input)
        command_row.addWidget(self.add_button)

        layout = QVBoxLayout()
        layout.addWidget(
            QLabel(
                "Enter nodes and members in the x-z plane. Canvas clicks snap to "
                "0.5 m; three gray dashes indicate the reference fiber (+local z). "
                "Supports use their DX, DZ, and RY restraints. Changes are "
                "recorded in the .mfs script."
            )
        )
        layout.addLayout(tool_row)
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
        self.select_tool_button.setChecked(True)
        self._set_canvas_mode("select")
        self._refresh_model_canvas()
        self._create_menu()
        self._create_toolbar()

    def _create_input_tool(
        self,
        label: str,
        object_name: str,
        mode: Literal["select", "node", "member"],
        layout: QHBoxLayout,
    ) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName(object_name)
        button.setCheckable(True)
        button.clicked.connect(lambda _: self._set_canvas_mode(mode))
        self.input_tool_group.addButton(button)
        layout.addWidget(button)
        return button

    def _set_canvas_mode(self, mode: Literal["select", "node", "member"]) -> None:
        self._member_start_node = None
        self.canvas_2d.set_pending_node(None)
        self.canvas_2d.set_mode(mode)
        messages = {
            "select": "Select mode: click a node to inspect its identifier.",
            "node": "Node mode: click the canvas to add a node (snap: 0.5 m).",
            "member": "Member mode: click two existing nodes in order.",
        }
        self.statusBar().showMessage(messages[mode])

    def _refresh_model_canvas(self) -> None:
        try:
            model = compile_commands(self.script_editor.toPlainText())
        except (TypeError, ValueError) as error:
            self._member_start_node = None
            self.canvas_2d.set_pending_node(None)
            self.canvas_2d.set_model(None)
            if self.script_editor.toPlainText().strip():
                self.statusBar().showMessage(f"2D view unavailable: {error}", 5000)
            return

        node_ids = _record_ids(model, "nodes")
        if self._member_start_node not in node_ids:
            self._member_start_node = None
            self.canvas_2d.set_pending_node(None)
        self.canvas_2d.set_model(model)

    def _add_canvas_node(self, x: float, z: float) -> None:
        try:
            model = compile_commands(self.script_editor.toPlainText())
        except (TypeError, ValueError) as error:
            self.statusBar().showMessage(f"Cannot add node: {error}", 5000)
            return

        node_id = _next_identifier("N", _record_ids(model, "nodes"))
        command = f"node {node_id} x={_format_number(x)} y=0 z={_format_number(z)}"
        self._append_model_command(command, "Could not add node")

    def _canvas_node_selected(self, node_id: str) -> None:
        if self.canvas_2d.mode != "member":
            self.statusBar().showMessage(f"Selected node {node_id}", 3000)
            return

        if self._member_start_node is None:
            self._member_start_node = node_id
            self.canvas_2d.set_pending_node(node_id)
            self.statusBar().showMessage(
                f"Start node {node_id} selected; click the end node."
            )
            return

        start_node = self._member_start_node
        if start_node == node_id:
            self.statusBar().showMessage(
                "Choose a different node for the member end.", 5000
            )
            return

        try:
            model = compile_commands(self.script_editor.toPlainText())
        except (TypeError, ValueError) as error:
            self.statusBar().showMessage(f"Cannot add member: {error}", 5000)
            return

        member_id = _next_identifier("M", _record_ids(model, "members"))
        command = (
            f"member {member_id} {start_node} {node_id} "
            "material=default section=default"
        )
        if self._append_model_command(command, "Could not add member"):
            self._member_start_node = None
            self.canvas_2d.set_pending_node(None)

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

        self.add_node_action = self.file_toolbar.addAction(
            _load_icon("newNode_icon_RFEM6.png"), "Add node"
        )
        self.add_node_action.setToolTip("Add a node to the model")
        self.add_node_action.triggered.connect(self.add_node)

        self.add_member_action = self.file_toolbar.addAction(
            _load_icon("newBeam_icon_RFEM6.png"), "Add member"
        )
        self.add_member_action.setToolTip("Add a member between two nodes")
        self.add_member_action.triggered.connect(self.add_member)

        self.add_support_action = self.file_toolbar.addAction(
            _load_icon("Support_icon_RFEM6.png"), "Add support"
        )
        self.add_support_action.setToolTip("Add a support at a node")
        self.add_support_action.triggered.connect(self.add_support)

        self.add_load_action = self.file_toolbar.addAction(
            _load_icon("NodeLoad_icon_RFEM6.png"), "Add distributed load"
        )
        self.add_load_action.setToolTip("Add a distributed member load")
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
        candidate = f"{existing.rstrip()}\n{command}" if existing.strip() else command
        try:
            compile_commands(candidate)
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, title, str(error))
            return False

        self.script_editor.setPlainText(candidate)
        self.script_editor.moveCursor(QTextCursor.MoveOperation.End)
        self.script_editor.document().setModified(True)
        self.statusBar().showMessage("Command recorded in the script.", 3000)
        return True

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

        command = (
            f"node {_script_token(node_name.text())} "
            f"x={_format_number(x_field.value())} y=0 "
            f"z={_format_number(z_field.value())}"
        )
        self._append_model_command(command, "Could not add node")

    def add_member(self) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        node_ids = _record_ids(model, "nodes")
        if len(node_ids) < 2:
            QMessageBox.information(
                self, "Add member", "Create at least two nodes first."
            )
            return

        member_name = QLineEdit(_next_identifier("M", _record_ids(model, "members")))
        member_name.setObjectName("member_name")
        start_node = QComboBox()
        start_node.setObjectName("member_start_node")
        start_node.addItems(node_ids)
        end_node = QComboBox()
        end_node.setObjectName("member_end_node")
        end_node.addItems(node_ids)
        end_node.setCurrentIndex(1)

        dialog = QDialog(self)
        dialog.setObjectName("add_member_dialog")
        dialog.setWindowTitle("Add member")
        form = QFormLayout(dialog)
        form.addRow("Member name", member_name)
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
            f"member {_script_token(member_name.text())} "
            f"{_script_token(start_node.currentText())} "
            f"{_script_token(end_node.currentText())} "
            "material=default section=default"
        )
        self._append_model_command(command, "Could not add member")

    def add_support(self) -> None:
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

        command = (
            f"support {_script_token(node.currentText())} "
            f"DX={str(dx.isChecked()).lower()} DY=true "
            f"DZ={str(dz.isChecked()).lower()} RX=true "
            f"RY={str(ry.isChecked()).lower()} RZ=true"
        )
        self._append_model_command(command, "Could not add support")

    def add_distributed_load(self) -> None:
        model = self._model_for_dialog()
        if model is None:
            return
        member_ids = _record_ids(model, "members")
        if not member_ids:
            QMessageBox.information(
                self, "Add distributed load", "Create a member first."
            )
            return

        members = model.get("members")
        if not isinstance(members, list):
            raise TypeError("Model members must be a list")

        def member_length(identifier: str) -> float:
            for record in members:
                if (
                    isinstance(record, dict)
                    and record.get("id") == identifier
                    and isinstance(record.get("length"), (float, int))
                    and not isinstance(record.get("length"), bool)
                ):
                    return float(record["length"])
            raise ValueError(f"Could not determine the length of member {identifier!r}")

        member = QComboBox()
        member.setObjectName("load_member")
        member.addItems(member_ids)
        direction = QComboBox()
        direction.setObjectName("load_direction")
        direction.addItems(("FZ", "FX"))
        value_start = _number_field(10_000)
        value_start.setObjectName("load_value_start")
        value_end = _number_field(10_000)
        value_end.setObjectName("load_value_end")
        position_start = _number_field(0, minimum=0)
        position_start.setObjectName("load_position_start")
        initial_length = member_length(member.currentText())
        position_end = _number_field(initial_length, minimum=0)
        position_end.setObjectName("load_position_end")

        def update_member_length(identifier: str) -> None:
            length = member_length(identifier)
            position_start.setMaximum(length)
            position_end.setMaximum(length)
            position_end.setValue(length)

        member.currentTextChanged.connect(update_member_length)

        dialog = QDialog(self)
        dialog.setObjectName("add_distributed_load_dialog")
        dialog.setWindowTitle("Add distributed load")
        form = QFormLayout(dialog)
        form.addRow("Member", member)
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
            f"load distributed {_script_token(member.currentText())} "
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
        self.statusBar().showMessage(f"Opened {path}", 3000)

    def save_script(self) -> bool:
        if self.current_script is None:
            return self.save_script_as()
        return self._save_to(self.current_script)

    def save_script_as(self) -> bool:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save MyFEM script",
            str(self.current_script or Path("model.mfs")),
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
