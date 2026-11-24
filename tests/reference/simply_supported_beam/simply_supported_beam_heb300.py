# AI created the file
# Author: Copilot, Johannes Kalliauer
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CEST: Author: Changes
# 2026-11-22 14:20 CET: Copilot: Added JSON model loading and English identifiers
# 2026-11-22 14:30 CET: Copilot: Applied Ruff formatting and import cleanup
# 2026-11-22 14:40 CET: Copilot: Converted the reference plane to the structural x-z plane
# 2026-11-22 14:52 CET: Copilot: Kept Pynite coordinates directly in the x-z plane
# 2026-11-22 15:08 CET: Copilot: Corrected the horizontal beam deflection output
# 2026-11-24 22:02 CET: Copilot: Updated the reference model to format 0.2 beams

import json
from pathlib import Path

from Pynite import FEModel3D

MODEL_PATH = Path(__file__).with_name("simply_supported_beam_heb300.json")


def load_model_data() -> dict:
    """Load the simply supported HEB 300 reference model in SI units."""
    with MODEL_PATH.open("r", encoding="utf-8") as model_file:
        return json.load(model_file)


def main() -> None:
    data = load_model_data()
    model = FEModel3D()

    for node in data["nodes"]:
        model.add_node(node["id"], node["x"], node["y"], node["z"])

    for material in data["materials"]:
        model.add_material(
            material["id"],
            material["E"],
            material["G"],
            material["nu"],
            material["rho"],
        )

    for section in data["sections"]:
        model.add_section(
            section["id"],
            section["A"],
            section["I_yy"],
            section["I_zz"],
            section["I_T"],
        )

    for beam in data["beams"]:
        model.add_member(
            beam["id"],
            beam["node_start"],
            beam["node_end"],
            beam["material"],
            beam["section"],
        )

    for support in data["supports"]:
        model.def_support(
            support["node"],
            support["DX"],
            support["DY"],
            support["DZ"],
            support["RX"],
            support["RY"],
            support["RZ"],
        )

    for load in data["loads"]:
        if load["direction"] != "FZ":
            raise ValueError("The 2D reference model supports loads in FZ only")
        model.add_member_dist_load(
            load["beam"],
            "FZ",
            load["value_start"],
            load["value_end"],
            load["position_start"],
            load["position_end"],
            case=load["case"],
        )

    for combination in data["load_combinations"]:
        model.add_load_combo(combination["id"], combination["cases"])

    model.analyze(check_statics=True)

    load = data["loads"][0]
    beam = data["beams"][0]
    left_node = data["supports"][0]["node"]
    right_node = data["supports"][1]["node"]
    section = data["sections"][0]
    material = data["materials"][0]
    span = beam["length"]
    distributed_load = abs(load["value_start"])

    analytical_reference = {
        "M_max": distributed_load * span**2 / 8,
        "deflection_max": (
            5 * distributed_load * span**4 / (384 * material["E"] * section["I_yy"])
        ),
    }

    print("=== SUPPORT REACTIONS (Load combination SLS) ===")
    print(
        f"{left_node} (left) : "
        f"FX = {model.nodes[left_node].RxnFX['SLS'] / 1000:.2f} kN, "
        f"FZ = {model.nodes[left_node].RxnFZ['SLS'] / 1000:.2f} kN"
    )
    print(
        f"{right_node} (right): "
        f"FX = {model.nodes[right_node].RxnFX['SLS'] / 1000:.2f} kN, "
        f"FZ = {model.nodes[right_node].RxnFZ['SLS'] / 1000:.2f} kN"
    )

    print("\n=== INTERNAL FORCES & DEFLECTION ===")
    analysed_beam = model.members[beam["id"]]
    print(
        f"Max. bending moment My (midspan): "
        f"{analysed_beam.max_moment('My', 'SLS') / 1000:.2f} kNm"
    )
    print(
        f"Min. bending moment My (midspan): "
        f"{analysed_beam.min_moment('My', 'SLS') / 1000:.2f} kNm"
    )
    print(
        f"Max. shear force Fz             : "
        f"{analysed_beam.max_shear('Fz', 'SLS') / 1000:.2f} kN"
    )
    print(
        f"Min. shear force Fz             : "
        f"{analysed_beam.min_shear('Fz', 'SLS') / 1000:.2f} kN"
    )
    print(
        "Max. deflection dz (midspan)    : "
        f"{analysed_beam.max_deflection('dz', 'SLS') * 1000:.2f} mm"
    )
    print(
        "Analytical M_max                : "
        f"{analytical_reference['M_max'] / 1000:.2f} kNm"
    )
    print(
        "Analytical deflection_max        : "
        f"{analytical_reference['deflection_max'] * 1000:.2f} mm"
    )


if __name__ == "__main__":
    main()
