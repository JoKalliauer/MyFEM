# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 19:28 CET: Copilot: Tested PyNite script generation and result logging

from pathlib import Path

from myfem.pynite_export import generate_and_run

REFERENCE_JSON = (
    Path(__file__).parent
    / "reference"
    / "simply_supported_beam"
    / "simply_supported_beam_heb300.json"
)


def test_generated_pynite_script_saves_results_to_log(tmp_path: Path) -> None:
    python_path = tmp_path / "model.py"
    log_path = tmp_path / "output.log"

    generate_and_run(REFERENCE_JSON, python_path, log_path)

    assert python_path.is_file()
    log = log_path.read_text(encoding="utf-8")
    assert "N1: FX=0.00 kN, FZ=-40.00 kN" in log
    assert "My max/min: 80.00 / 0.00 kNm" in log
    assert "dz max: 10.09 mm" in log
