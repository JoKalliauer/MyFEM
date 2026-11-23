# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:40 CET: Copilot: Added command script compilation tests
# 2026-11-23 21:17 CET: Copilot: Tested fallback properties and combinations
# 2026-11-23 21:33 CET: Copilot: Tested format version 0.1
# 2026-11-23 21:53 CET: Copilot: Tested default and explicit precision settings
# 2026-11-23 21:53 CET: Copilot: Tested precision defaults with format 0.1

from pathlib import Path

import pytest

from myfem.script import compile_commands, compile_script, write_model

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


def test_missing_default_properties_are_added_with_provenance() -> None:
    model = compile_commands(
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "member M1 N1 N2\n"
        "load distributed M1 direction=FZ value_start=10000 value_end=10000 "
        "position_start=0 position_end=8 case=default\n"
    )

    assert model["format_version"] == 0.1
    assert model["materials"] == [
        {
            "id": "default",
            "E": 210_000_000_000,
            "G": 80_770_000_000,
            "nu": 0.3,
            "rho": 78_500,
            "auto_generated": True,
        }
    ]
    assert model["sections"] == [
        {
            "id": "default",
            "A": 0.01491,
            "I_yy": 0.0002517,
            "I_zz": 0.00008563,
            "I_T": 0.00000185,
            "auto_generated": True,
        }
    ]
    member = model["members"][0]
    assert member["material_was_default"] is True
    assert member["section_was_default"] is True
    assert model["load_combinations"] == [
        {
            "id": "SLS",
            "cases": {"default": 1.0},
            "generated_default": True,
        }
    ]
    assert model["precision"] == {
        "absolute": 0.0,
        "relative": 1e-12,
        "defaulted": True,
    }


def test_precision_options_can_be_set_together_or_separately() -> None:
    combined = compile_commands(
        "precision absolute=1e-11 relative=1e-12\nnode N1 x=0 y=0 z=0\n"
    )
    assert combined["precision"] == {
        "absolute": 1e-11,
        "relative": 1e-12,
        "defaulted": False,
    }

    model = compile_commands(
        "precision absolute=1e-11\nprecision relative=1e-12\nnode N1 x=0 y=0 z=0\n"
    )

    assert model["precision"] == {
        "absolute": 1e-11,
        "relative": 1e-12,
        "defaulted": False,
    }

    with pytest.raises(ValueError, match="must not be negative"):
        compile_commands("precision relative=-1\n")
    with pytest.raises(ValueError, match="specified more than once"):
        compile_commands("precision absolute=1e-11\nprecision absolute=1e-12\n")


def test_default_uses_a_single_named_property_definition() -> None:
    model = compile_commands(
        "material structural_steel E=2.1e11 G=8.077e10 nu=0.3 rho=78500\n"
        "section custom A=0.01491 I_yy=0.0002517 I_zz=0.00008563 I_T=0.00000185\n"
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "member M1 N1 N2 material=default section=default\n"
    )

    assert model["members"][0]["material"] == "structural_steel"
    assert model["members"][0]["section"] == "custom"
    assert model["members"][0]["material_was_default"] is True
    assert model["members"][0]["section_was_default"] is True
    assert model["materials"][0].get("auto_generated", False) is False
    assert model["sections"][0].get("auto_generated", False) is False


def test_default_is_ambiguous_with_multiple_unnamed_definitions() -> None:
    with pytest.raises(ValueError, match="No material named 'default' exists"):
        compile_commands(
            "material steel E=2.1e11 G=8.077e10 nu=0.3 rho=78500\n"
            "material aluminum E=7.0e10 G=2.6e10 nu=0.33 rho=2700\n"
            "node N1 x=0 y=0 z=0\n"
            "node N2 x=8 y=0 z=0\n"
            "member M1 N1 N2 material=default section=default\n"
        )
    with pytest.raises(ValueError, match="No section named 'default' exists"):
        compile_commands(
            "section HEA A=0.01 I_yy=0.0001 I_zz=0.00005 I_T=0.000001\n"
            "section HEB A=0.02 I_yy=0.0002 I_zz=0.0001 I_T=0.000002\n"
            "node N1 x=0 y=0 z=0\n"
            "node N2 x=8 y=0 z=0\n"
            "member M1 N1 N2 material=default section=default\n"
        )


def test_missing_combination_requires_default_load_case() -> None:
    with pytest.raises(
        ValueError,
        match=r"default SLS combination can only be generated for load case "
        r"'default'; found: G",
    ):
        compile_commands(
            "material steel E=2.1e11 G=8.077e10 nu=0.3 rho=78500\n"
            "section HEB A=0.01491 I_yy=0.0002517 I_zz=0.00008563 I_T=0.00000185\n"
            "node N1 x=0 y=0 z=0\n"
            "node N2 x=8 y=0 z=0\n"
            "member M1 N1 N2 material=steel section=HEB\n"
            "load distributed M1 direction=FZ value_start=10000 value_end=10000 "
            "position_start=0 position_end=8 case=G\n"
        )
