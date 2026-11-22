# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:40 CET: Copilot: Added command script compilation tests

from pathlib import Path

import pytest

from myfem.script import compile_script, write_model

REFERENCE_DIRECTORY = Path(__file__).parent / "reference" / "simply_supported_beam"


def test_reference_commands_generate_reference_json(tmp_path: Path) -> None:
    script = REFERENCE_DIRECTORY / "simply_supported_beam_heb300.mfs"
    expected_path = REFERENCE_DIRECTORY / "simply_supported_beam_heb300.json"
    output = tmp_path / "model.json"

    write_model(script, output)

    assert output.read_text(encoding="utf-8") == expected_path.read_text(
        encoding="utf-8"
    )


def test_script_errors_include_source_line(tmp_path: Path) -> None:
    script = tmp_path / "invalid.mfs"
    script.write_text("unknown_command\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"invalid\.mfs:1: Unknown command"):
        compile_script(script)
