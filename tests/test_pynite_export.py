# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 19:28 CET: Copilot: Tested PyNite script generation and result logging
# 2026-11-22 19:40 CET: Copilot: Checked .out result filenames
# 2026-11-23 21:17 CET: Copilot: Tested fallback result suppression and migration
# 2026-11-23 21:33 CET: Copilot: Tested migration to format version 0.1
# 2026-11-23 21:53 CET: Copilot: Tested precision defaults and result normalization
# 2026-11-23 21:53 CET: Copilot: Tested precision output and legacy migration
# 2026-11-23 22:15 CET: Copilot: Tested centered statics output cells

import json
from pathlib import Path

import pytest

from myfem.pynite_export import generate_and_run, generate_python_script
from myfem.script import write_model

REFERENCE_JSON = (
    Path(__file__).parent
    / "reference"
    / "simply_supported_beam"
    / "simply_supported_beam_heb300.json"
)


def test_generated_pynite_script_saves_results_to_log(tmp_path: Path) -> None:
    python_path = tmp_path / "model.py"
    log_path = tmp_path / "model.out"

    generate_and_run(REFERENCE_JSON, python_path, log_path)

    assert python_path.is_file()
    log = log_path.read_text(encoding="utf-8")
    assert "N1: FX=0.00 kN, FZ=-40.00 kN" in log
    assert "My max/min: 80.00 / 0.00 kNm" in log
    assert "dz max: 10.09 mm" in log


def test_fallback_properties_omit_deformation_results(tmp_path: Path) -> None:
    script_path = tmp_path / "default_model.mfs"
    script_path.write_text(
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "member M1 N1 N2 material=default section=default\n"
        "support N1 DX=true DY=true DZ=true RX=true RY=false RZ=true\n"
        "support N2 DX=false DY=true DZ=true RX=true RY=false RZ=true\n"
        "load distributed M1 direction=FZ value_start=10000 value_end=10000 "
        "position_start=0 position_end=8 case=default\n",
        encoding="utf-8",
    )
    model_path = script_path.with_suffix(".json")
    write_model(script_path, model_path)

    python_path = script_path.with_suffix(".py")
    output_path = script_path.with_suffix(".out")
    generate_and_run(model_path, python_path, output_path)
    output = output_path.read_text(encoding="utf-8")

    generated_source = python_path.read_text(encoding="utf-8")
    assert "generated_default" not in generated_source
    assert (
        "# MyFEM generated the default SLS combination (default=1)." in generated_source
    )
    assert "Deflections and rotations omitted" in output
    assert "dz max:" not in output


@pytest.mark.parametrize(
    ("precision_command", "expected_precision"),
    (
        (
            "",
            {"absolute": 0.0, "relative": 1e-12, "defaulted": True},
        ),
        (
            "precision absolute=1e-11 relative=0\n",
            {"absolute": 1e-11, "relative": 0.0, "defaulted": False},
        ),
    ),
)
def test_precision_suppresses_small_statics_residual(
    tmp_path: Path,
    precision_command: str,
    expected_precision: dict[str, object],
) -> None:
    script_path = tmp_path / "small_residual.mfs"
    script_path.write_text(
        precision_command + "node N1 x=-4 y=0 z=3\n"
        "node rechts x=4 y=0 z=3\n"
        "member M1 N1 rechts material=default section=default\n"
        "support N1 DX=true DY=true DZ=true RX=true RY=false RZ=true\n"
        "support rechts DX=false DY=true DZ=true RX=true RY=false RZ=true\n"
        "load distributed M1 direction=FZ value_start=1000 value_end=1000 "
        "position_start=0 position_end=8 case=default\n",
        encoding="utf-8",
    )
    model_path = script_path.with_suffix(".json")
    write_model(script_path, model_path)

    model_data = json.loads(model_path.read_text(encoding="utf-8"))
    assert model_data["precision"] == expected_precision

    generate_and_run(
        model_path, script_path.with_suffix(".py"), script_path.with_suffix(".out")
    )
    output = script_path.with_suffix(".out").read_text(encoding="utf-8")
    lines = output.splitlines()
    headers = [
        cell.strip()
        for cell in next(line for line in lines if "Sum FX" in line).split("|")[1:-1]
    ]
    row = next(
        line.split("|")[1:-1]
        for line in lines
        if line.startswith("|") and line.split("|")[1].strip() == "SLS"
    )
    statics_row = [cell.strip() for cell in row]

    assert statics_row[headers.index("Sum RMY")] == "0"
    rmy_cell = row[headers.index("Sum RMY")]
    assert rmy_cell == f"{'0':^{len(rmy_cell)}}"
    assert statics_row[headers.index("Sum FZ")] == "8e+03"
    assert "-3.64e-12" not in output


def test_single_named_property_definition_keeps_deformation_results(
    tmp_path: Path,
) -> None:
    script_path = tmp_path / "named_default.mfs"
    script_path.write_text(
        "material steel E=210000000000 G=80770000000 nu=0.3 rho=78500\n"
        "section HEB A=0.01491 I_yy=0.0002517 I_zz=0.00008563 I_T=0.00000185\n"
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "member M1 N1 N2 material=default section=default\n"
        "support N1 DX=true DY=true DZ=true RX=true RY=false RZ=true\n"
        "support N2 DX=false DY=true DZ=true RX=true RY=false RZ=true\n"
        "load distributed M1 direction=FZ value_start=10000 value_end=10000 "
        "position_start=0 position_end=8 case=default\n",
        encoding="utf-8",
    )
    model_path = script_path.with_suffix(".json")
    write_model(script_path, model_path)

    generate_and_run(
        model_path, script_path.with_suffix(".py"), script_path.with_suffix(".out")
    )
    output = script_path.with_suffix(".out").read_text(encoding="utf-8")

    assert "dz max:" in output
    assert "Deflections and rotations omitted" not in output


@pytest.mark.parametrize("legacy_version", (0.1, 1, 2))
def test_legacy_json_versions_are_migrated(
    tmp_path: Path, legacy_version: float
) -> None:
    data = json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))
    data["format_version"] = legacy_version
    model_path = tmp_path / "legacy.json"
    model_path.write_text(json.dumps(data), encoding="utf-8")

    python_path = tmp_path / "migrated.py"
    generate_python_script(model_path, python_path, tmp_path / "legacy.out")
    generated_source = python_path.read_text(encoding="utf-8")

    assert '"format_version":0.1' in generated_source
    assert '"auto_generated":false' in generated_source
    assert "generated_default" not in generated_source
    assert "# MyFEM generated the default SLS combination" not in generated_source
    assert (
        '"precision":{"absolute":0.0,"relative":1e-12,"defaulted":true}'
        in generated_source
    )


def test_no_combination_with_non_default_case_is_rejected(tmp_path: Path) -> None:
    data = json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))
    data["load_combinations"] = []
    data["loads"][0]["case"] = "G"
    model_path = tmp_path / "no_default_case.json"
    model_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="only be generated for load case 'default'"):
        generate_python_script(
            model_path, tmp_path / "model.py", tmp_path / "model.out"
        )
