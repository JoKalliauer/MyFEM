# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:45 CET: Copilot: Added command-script editor and JSON export
# 2026-11-22 19:40 CET: Copilot: Added Calculate action and .out results

"""Command-oriented MyFEM window for recording replayable model scripts."""

import subprocess
from pathlib import Path

from PySide6.QtGui import QCloseEvent, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from myfem.pynite_export import generate_and_run
from myfem.script import compile_commands, write_model


class MainWindow(QMainWindow):
    """Edit a MyFEM command log and generate its model JSON."""

    def __init__(self) -> None:
        super().__init__()
        self.current_script: Path | None = None
        self.setWindowTitle("MyFEM command editor[*]")
        self.resize(900, 600)

        self.script_editor = QPlainTextEdit()
        self.script_editor.setPlaceholderText(
            "Recorded model commands will appear here."
        )
        self.script_editor.document().modificationChanged.connect(
            self.setWindowModified
        )

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText(
            "Enter a command, e.g. node N1 x=0 y=0 z=0"
        )
        self.add_button = QPushButton("Add command")
        self.add_button.clicked.connect(self._add_command)
        self.command_input.returnPressed.connect(self._add_command)

        self.open_button = QPushButton("Open script")
        self.open_button.clicked.connect(lambda: self.open_script())
        self.save_button = QPushButton("Save script")
        self.save_button.clicked.connect(lambda: self.save_script())
        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.calculate)

        command_row = QHBoxLayout()
        command_row.addWidget(self.command_input)
        command_row.addWidget(self.add_button)

        file_row = QHBoxLayout()
        file_row.addWidget(self.open_button)
        file_row.addWidget(self.save_button)
        file_row.addWidget(self.calculate_button)

        layout = QVBoxLayout()
        layout.addWidget(
            QLabel(
                "Each accepted model command is appended to the replayable .mfs "
                "script. Calculate saves the script, generates JSON and Python, "
                "runs PyNite, and writes the results to a .out file."
            )
        )
        layout.addWidget(self.script_editor)
        layout.addLayout(command_row)
        layout.addLayout(file_row)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self._create_menu()

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
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

    def _add_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            return

        existing = self.script_editor.toPlainText()
        candidate = f"{existing.rstrip()}\n{command}" if existing.strip() else command
        try:
            compile_commands(candidate)
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Invalid command", str(error))
            return

        self.script_editor.setPlainText(candidate)
        self.script_editor.moveCursor(QTextCursor.MoveOperation.End)
        self.script_editor.document().setModified(True)
        self.command_input.clear()
        self.statusBar().showMessage("Command recorded in the script.", 3000)

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
        if path.suffix == "":
            path = path.with_suffix(".mfs")
        return self._save_to(path)

    def _save_to(self, path: Path) -> bool:
        try:
            path.write_text(self.script_editor.toPlainText() + "\n", encoding="utf-8")
        except OSError as error:
            QMessageBox.critical(self, "Could not save script", str(error))
            return False

        self.current_script = path
        self.script_editor.document().setModified(False)
        self.statusBar().showMessage(f"Saved {path}", 3000)
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
            write_model(script_path, model_path)
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
