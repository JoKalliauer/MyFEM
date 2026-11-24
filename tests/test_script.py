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
# 2026-11-24 22:02 CET: Copilot: Tested beam commands and format version 0.2
# 2026-11-24 23:05 CET: Copilot: Tested node-on-beam splitting and load remapping
# 2026-11-24 23:15 CET: Copilot: Tested concise model defaults and deletion helpers
# 2026-11-24 23:39 CET: Copilot: Tests timestamped model format versions

import json
from pathlib import Path

import pytest

from myfem.script import (
    beams_at_point,
    compile_commands,
    compile_script,
    delete_node_from_script,
    delete_support_from_script,
    split_beams_at_node,
    write_model,
)
from myfem.versioning import FORMAT_VERSION, format_package_version

REFERENCE_DIRECTORY = Path(__file__).parent / "reference" / "simply_supported_beam"


def test_reference_commands_generate_reference_json(tmp_path: Path) -> None:
    script = REFERENCE_DIRECTORY / "simply_supported_beam_heb300.mfs"
    expected_path = REFERENCE_DIRECTORY / "simply_supported_beam_heb300.json"
    output = tmp_path / "model.json"

    write_model(script, output)

    assert output.read_text(encoding="utf-8") == expected_path.read_text(
        encoding="utf-8"
    )
    model = json.loads(output.read_text(encoding="utf-8"))
    assert model["format_version"] == FORMAT_VERSION
    assert "members" not in model
    assert model["beams"][0]["id"] == "M1"


def test_script_errors_include_source_line(tmp_path: Path) -> None:
    script = tmp_path / "invalid.mfs"
    script.write_text("unknown_command\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"invalid\.mfs:1: Unknown command"):
        compile_script(script)


def test_previous_member_command_is_not_supported() -> None:
    with pytest.raises(ValueError, match="Unknown command 'member'"):
        compile_commands("member M1 N1 N2\n")


@pytest.mark.parametrize(
    ("package_version", "display_version"),
    (
        ("0.2", "0.2"),
        ("0.2.2026", "0.2.2026"),
        ("0.2.2026.11", "0.2.2026-11"),
        ("0.2.2026.11.24", "0.2.2026-11-24"),
        ("0.2.2026.11.24.23", "0.2.2026-11-24_23"),
        ("0.2.2026.11.24.23.39", "0.2.2026-11-24_23-39"),
    ),
)
def test_package_versions_use_canonical_date_display(
    package_version: str, display_version: str
) -> None:
    assert format_package_version(package_version) == display_version


def test_package_version_rejects_invalid_date_components() -> None:
    with pytest.raises(ValueError, match="valid date suffix"):
        format_package_version("0.2.2026.13")


def test_model_declaration_and_2d_defaults_are_compiled() -> None:
    model = compile_commands(
        "model 2D xz x=right z=down\n"
        "node N1 x=0 z=0\n"
        "support N1 DX=true DZ=false RY=false"
    )

    assert model["nodes"] == [{"id": "N1", "x": 0.0, "y": 0.0, "z": 0.0}]
    assert model["supports"] == [
        {
            "node": "N1",
            "DX": True,
            "DY": True,
            "DZ": False,
            "RX": True,
            "RY": False,
            "RZ": True,
        }
    ]

    with pytest.raises(ValueError, match="model syntax"):
        compile_commands("model 3D xyz x=right y=up z=down\n")
    with pytest.raises(ValueError, match="only appear once"):
        compile_commands("model 2D xz x=right z=down\nmodel 2D xz x=right z=down\n")


def test_delete_node_removes_connected_beams_loads_and_support() -> None:
    source = (
        "node N1 x=0 z=0\n"
        "node N2 x=4 z=0\n"
        "node N3 x=8 z=0\n"
        "beam B1 N1 N2\n"
        "beam B2 N2 N3\n"
        "load distributed B1 direction=FZ value_start=1 value_end=1 "
        "position_start=0 position_end=4 case=default\n"
        "support N1 DX=true DZ=true RY=false\n"
        "# retain this note"
    )

    result = delete_node_from_script(source, "N1")
    model = compile_commands(result)

    assert [node["id"] for node in model["nodes"]] == ["N2", "N3"]
    assert [beam["id"] for beam in model["beams"]] == ["B2"]
    assert model["loads"] == []
    assert model["supports"] == []
    assert "# retain this note" in result
    with pytest.raises(ValueError, match="not found"):
        delete_node_from_script(result, "N1")


def test_delete_support_removes_only_the_selected_support() -> None:
    source = (
        "node N1 x=0 z=0\n"
        "node N2 x=1 z=0\n"
        "support N1 DX=true DZ=true RY=false\n"
        "support N2 DX=true DZ=true RY=false"
    )

    result = delete_support_from_script(source, "N1")
    assert [support["node"] for support in compile_commands(result)["supports"]] == [
        "N2"
    ]


def test_beams_at_point_only_matches_beam_interiors() -> None:
    source = "node N1 x=0 y=0 z=0\nnode N2 x=8 y=0 z=0\nbeam B1 N1 N2"

    assert beams_at_point(source, 4, 0) == ["B1"]
    assert beams_at_point(source, 0, 0) == []
    assert beams_at_point(source, 4, 0.01) == []


def test_split_beam_uses_suffixes_based_on_id_ending() -> None:
    digit_ending_source = (
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "beam B1 N1 N2 material=default section=default # original beam"
    )
    split_digit_ending = split_beams_at_node(
        digit_ending_source, "node N3 x=4 y=0 z=0", ["B1"]
    )
    assert "beam B1a N1 N3" in split_digit_ending
    assert "beam B1b N3 N2" in split_digit_ending
    assert "material=default section=default # original beam" in split_digit_ending

    letter_ending_source = "node N1 x=0 y=0 z=0\nnode N2 x=8 y=0 z=0\nbeam B1a N1 N2"
    split_letter_ending = split_beams_at_node(
        letter_ending_source, "node N3 x=4 y=0 z=0", ["B1a"]
    )
    assert "beam B1a0 N1 N3" in split_letter_ending
    assert "beam B1a1 N3 N2" in split_letter_ending


def test_split_beam_skips_colliding_pair_of_ids() -> None:
    source = (
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "node N3 x=0 y=0 z=2\n"
        "node N4 x=8 y=0 z=2\n"
        "beam B1 N1 N2\n"
        "beam B1a N3 N4"
    )

    result = split_beams_at_node(source, "node N5 x=4 y=0 z=0", ["B1"])

    assert "beam B1c N1 N5" in result
    assert "beam B1d N5 N2" in result
    model = compile_commands(result)
    assert {beam["id"] for beam in model["beams"]} == {"B1a", "B1c", "B1d"}


def test_split_letter_ending_beam_skips_colliding_numeric_pair() -> None:
    source = (
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "node N3 x=0 y=0 z=2\n"
        "node N4 x=8 y=0 z=2\n"
        "beam B1a N1 N2\n"
        "beam B1a0 N3 N4"
    )

    result = split_beams_at_node(source, "node N5 x=4 y=0 z=0", ["B1a"])

    assert "beam B1a2 N1 N5" in result
    assert "beam B1a3 N5 N2" in result
    model = compile_commands(result)
    assert {beam["id"] for beam in model["beams"]} == {
        "B1a0",
        "B1a2",
        "B1a3",
    }


def test_split_beam_preserves_distributed_load_across_both_segments() -> None:
    source = (
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "beam B1 N1 N2\n"
        "load distributed B1 direction=FZ value_start=5 value_end=5 "
        "position_start=0 position_end=2 case=default # left\n"
        "load distributed B1 direction=FZ value_start=10 value_end=30 "
        "position_start=2 position_end=6 case=default # spanning\n"
        "load distributed B1 direction=FX value_start=4 value_end=4 "
        "position_start=5 position_end=7 case=default # right"
    )

    result = split_beams_at_node(source, "node N3 x=4 y=0 z=0", ["B1"])
    model = compile_commands(result)

    assert model["loads"] == [
        {
            "type": "beam_distributed",
            "beam": "B1a",
            "direction": "FZ",
            "value_start": 5.0,
            "value_end": 5.0,
            "position_start": 0.0,
            "position_end": 2.0,
            "case": "default",
        },
        {
            "type": "beam_distributed",
            "beam": "B1a",
            "direction": "FZ",
            "value_start": 10.0,
            "value_end": 20.0,
            "position_start": 2.0,
            "position_end": 4.0,
            "case": "default",
        },
        {
            "type": "beam_distributed",
            "beam": "B1b",
            "direction": "FZ",
            "value_start": 20.0,
            "value_end": 30.0,
            "position_start": 0.0,
            "position_end": 2.0,
            "case": "default",
        },
        {
            "type": "beam_distributed",
            "beam": "B1b",
            "direction": "FX",
            "value_start": 4.0,
            "value_end": 4.0,
            "position_start": 1.0,
            "position_end": 3.0,
            "case": "default",
        },
    ]
    assert "# spanning" in result
    assert "# right" in result


def test_missing_default_properties_are_added_with_provenance() -> None:
    model = compile_commands(
        "node N1 x=0 y=0 z=0\n"
        "node N2 x=8 y=0 z=0\n"
        "beam B1 N1 N2\n"
        "load distributed B1 direction=FZ value_start=10000 value_end=10000 "
        "position_start=0 position_end=8 case=default\n"
    )

    assert model["format_version"] == FORMAT_VERSION
    assert "members" not in model
    assert model["beams"][0]["id"] == "B1"
    assert model["loads"][0]["beam"] == "B1"
    assert model["loads"][0]["type"] == "beam_distributed"
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
    beam = model["beams"][0]
    assert beam["material_was_default"] is True
    assert beam["section_was_default"] is True
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
        "beam B1 N1 N2 material=default section=default\n"
    )

    assert model["beams"][0]["material"] == "structural_steel"
    assert model["beams"][0]["section"] == "custom"
    assert model["beams"][0]["material_was_default"] is True
    assert model["beams"][0]["section_was_default"] is True
    assert model["materials"][0].get("auto_generated", False) is False
    assert model["sections"][0].get("auto_generated", False) is False


def test_default_is_ambiguous_with_multiple_unnamed_definitions() -> None:
    with pytest.raises(ValueError, match="No material named 'default' exists"):
        compile_commands(
            "material steel E=2.1e11 G=8.077e10 nu=0.3 rho=78500\n"
            "material aluminum E=7.0e10 G=2.6e10 nu=0.33 rho=2700\n"
            "node N1 x=0 y=0 z=0\n"
            "node N2 x=8 y=0 z=0\n"
            "beam B1 N1 N2 material=default section=default\n"
        )
    with pytest.raises(ValueError, match="No section named 'default' exists"):
        compile_commands(
            "section HEA A=0.01 I_yy=0.0001 I_zz=0.00005 I_T=0.000001\n"
            "section HEB A=0.02 I_yy=0.0002 I_zz=0.0001 I_T=0.000002\n"
            "node N1 x=0 y=0 z=0\n"
            "node N2 x=8 y=0 z=0\n"
            "beam B1 N1 N2 material=default section=default\n"
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
            "beam B1 N1 N2 material=steel section=HEB\n"
            "load distributed B1 direction=FZ value_start=10000 value_end=10000 "
            "position_start=0 position_end=8 case=G\n"
        )
