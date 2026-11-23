# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:45 CET: Copilot: Added the GUI application entry point
# 2026-11-23 22:17 CET: Copilot: Filtered repetitive Wayland text-input warnings

import os
import sys

from PySide6.QtWidgets import QApplication

from myfem.gui.main_window import MainWindow


def _configure_wayland_textinput_logging() -> None:
    if not os.environ.get("WAYLAND_DISPLAY"):
        return

    rule = "qt.qpa.wayland.textinput.warning=false"
    rules = os.environ.get("QT_LOGGING_RULES", "").strip()
    existing_rules = [
        item.strip() for item in rules.replace("\n", ";").split(";") if item.strip()
    ]
    if any(
        item.startswith("qt.qpa.wayland.textinput.warning=") for item in existing_rules
    ):
        return

    os.environ["QT_LOGGING_RULES"] = f"{rules};{rule}" if rules else rule


def main() -> int:
    _configure_wayland_textinput_logging()
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
