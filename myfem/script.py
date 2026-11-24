# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-22

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-22 18:40 CET: Copilot: Added replayable model command scripts
# 2026-11-23 21:17 CET: Copilot: Added default properties and provenance
# 2026-11-23 21:33 CET: Copilot: Set model format version to 0.1
# 2026-11-23 21:53 CET: Copilot: Added precision defaults while retaining format 0.1
# 2026-11-24 22:02 CET: Copilot: Renamed model members to beams in format 0.2
# 2026-11-24 23:05 CET: Copilot: Added node-on-beam splitting with load preservation
# 2026-11-24 23:15 CET: Copilot: Added model declaration and concise GUI defaults
# 2026-11-24 23:39 CET: Copilot: Writes timestamped 0.2 format versions

"""Compile MyFEM command scripts into deterministic JSON model files."""

import argparse
import json
import math
import shlex
from pathlib import Path

from myfem.versioning import FORMAT_VERSION

_DEFAULT_MATERIAL = {
    "E": 210_000_000_000,
    "G": 80_770_000_000,
    "nu": 0.3,
    "rho": 78_500,
}
_DEFAULT_SECTION = {
    "A": 0.01491,
    "I_yy": 0.0002517,
    "I_zz": 0.00008563,
    "I_T": 0.00000185,
}
_BEAM_SPLIT_TOLERANCE = 1e-6


def _parse_value(value: str) -> float | bool | str:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        number = float(value)
    except ValueError:
        return value
    if not math.isfinite(number):
        raise ValueError(f"Expected a finite number, got {value!r}")
    return number


def _parse_options(tokens: list[str]) -> dict[str, float | bool | str]:
    options: dict[str, float | bool | str] = {}
    for token in tokens:
        key, separator, value = token.partition("=")
        if not separator or not key or not value:
            raise ValueError(f"Expected key=value, got {token!r}")
        if key in options:
            raise ValueError(f"Option {key!r} was specified more than once")
        options[key] = _parse_value(value)
    return options


def _required(
    options: dict[str, float | bool | str],
    required_keys: tuple[str, ...],
    optional_keys: tuple[str, ...] = (),
) -> dict[str, float | bool | str]:
    missing = set(required_keys) - options.keys()
    extra = options.keys() - set(required_keys + optional_keys)
    if missing:
        raise ValueError(f"Missing option(s): {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"Unknown option(s): {', '.join(sorted(extra))}")
    return options


def _number(value: float | bool | str, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, float):
        raise TypeError(f"Option {key!r} must be a number")
    return value


def _identifier(value: float | bool | str, key: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"Option {key!r} must be an identifier")
    return value


def _split_command_comment(line: str) -> tuple[str, str]:
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


def _script_line(tokens: list[str], indentation: str, comment: str = "") -> str:
    command = " ".join(shlex.quote(token) for token in tokens)
    comment_suffix = f" {comment.lstrip()}" if comment else ""
    return f"{indentation}{command}{comment_suffix}"


def _node_position(
    model: dict[str, object], node_id: str
) -> tuple[float, float, float]:
    nodes = model.get("nodes")
    if not isinstance(nodes, list):
        raise TypeError("Model nodes must be a list")
    for node in nodes:
        if isinstance(node, dict) and node.get("id") == node_id:
            x = node.get("x")
            y = node.get("y")
            z = node.get("z")
            if (
                isinstance(x, bool)
                or not isinstance(x, (int, float))
                or isinstance(y, bool)
                or not isinstance(y, (int, float))
                or isinstance(z, bool)
                or not isinstance(z, (int, float))
            ):
                raise TypeError(f"Node {node_id!r} must have numeric x, y, and z")
            return float(x), float(y), float(z)
    raise ValueError(f"Unknown node {node_id!r}")


def _beam_split_position(
    model: dict[str, object], beam: dict[str, object], node_id: str
) -> tuple[float, float] | None:
    start_id = beam.get("node_start")
    end_id = beam.get("node_end")
    beam_id = beam.get("id")
    if not isinstance(start_id, str) or not isinstance(end_id, str):
        raise TypeError(f"Beam {beam_id!r} must define its endpoint nodes")
    start_x, start_y, start_z = _node_position(model, start_id)
    end_x, end_y, end_z = _node_position(model, end_id)
    node_x, node_y, node_z = _node_position(model, node_id)
    delta_x = end_x - start_x
    delta_y = end_y - start_y
    delta_z = end_z - start_z
    length = math.sqrt(delta_x**2 + delta_y**2 + delta_z**2)
    projection = (
        (node_x - start_x) * delta_x
        + (node_y - start_y) * delta_y
        + (node_z - start_z) * delta_z
    ) / (length * length)
    distance_x = node_x - start_x - projection * delta_x
    distance_y = node_y - start_y - projection * delta_y
    distance_z = node_z - start_z - projection * delta_z
    if (
        not 0 < projection < 1
        or math.sqrt(distance_x**2 + distance_y**2 + distance_z**2)
        > _BEAM_SPLIT_TOLERANCE
    ):
        return None
    return projection * length, length


def beams_at_point(text: str, x: float, z: float) -> list[str]:
    """Return beam IDs whose interior contains the given x-z position."""
    model = compile_commands(text)
    nodes = model.get("nodes")
    beams = model.get("beams")
    if not isinstance(nodes, list) or not isinstance(beams, list):
        raise TypeError("Model nodes and beams must be lists")
    probe_id = "__split_probe__"
    node_ids = {
        node["id"]
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    while probe_id in node_ids:
        probe_id = f"_{probe_id}"
    point_model = {
        **model,
        "nodes": [
            {"id": probe_id, "x": x, "y": 0.0, "z": z},
            *nodes,
        ],
    }
    matches: list[str] = []
    for beam in beams:
        if not isinstance(beam, dict) or not isinstance(beam.get("id"), str):
            raise TypeError("Each model beam must have a string id")
        if _beam_split_position(point_model, beam, probe_id) is not None:
            matches.append(beam["id"])
    return matches


def _alpha_suffix(number: int) -> str:
    suffix = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        suffix = chr(ord("a") + remainder) + suffix
    return suffix


def _split_beam_ids(beam_id: str, existing_ids: set[str]) -> tuple[str, str]:
    if not beam_id:
        raise ValueError("Beam IDs must not be empty")
    if beam_id[-1].isdigit():
        pair = 0
        while True:
            left = f"{beam_id}{_alpha_suffix(pair + 1)}"
            right = f"{beam_id}{_alpha_suffix(pair + 2)}"
            if left not in existing_ids and right not in existing_ids:
                return left, right
            pair += 2
    else:
        pair = 0
        while True:
            left = f"{beam_id}{pair}"
            right = f"{beam_id}{pair + 1}"
            if left not in existing_ids and right not in existing_ids:
                return left, right
            pair += 2
    raise ValueError(f"Could not find unused beam IDs for splitting {beam_id!r}")


def split_beams_at_node(text: str, node_command: str, beam_ids: list[str]) -> str:
    """Insert a node and split selected beams, preserving their distributed loads."""
    if not beam_ids:
        raise ValueError("At least one beam must be selected for splitting")
    if len(set(beam_ids)) != len(beam_ids):
        raise ValueError("Beam IDs to split must be unique")

    separator = "" if not text or text.endswith("\n") else "\n"
    candidate_source = f"{text}{separator}{node_command}"
    node_tokens = shlex.split(node_command)
    if len(node_tokens) < 2 or node_tokens[0] != "node":
        raise ValueError("The added command must define a node")
    node_id = node_tokens[1]
    model = compile_commands(candidate_source)
    beams = model.get("beams")
    if not isinstance(beams, list):
        raise TypeError("Model beams must be a list")
    beam_records = {
        beam["id"]: beam
        for beam in beams
        if isinstance(beam, dict) and isinstance(beam.get("id"), str)
    }
    if any(beam_id not in beam_records for beam_id in beam_ids):
        missing = next(beam_id for beam_id in beam_ids if beam_id not in beam_records)
        raise ValueError(f"Unknown beam {missing!r}")

    beam_ids_in_use = set(beam_records)
    splits: dict[str, tuple[str, str, float, float]] = {}
    for beam_id in beam_ids:
        beam = beam_records[beam_id]
        split_position = _beam_split_position(model, beam, node_id)
        if split_position is None:
            raise ValueError(f"Node {node_id!r} does not lie inside beam {beam_id!r}")
        distance, length = split_position
        left_id, right_id = _split_beam_ids(beam_id, beam_ids_in_use)
        beam_ids_in_use.remove(beam_id)
        beam_ids_in_use.update((left_id, right_id))
        splits[beam_id] = (left_id, right_id, distance, length)

    transformed_lines: list[str] = []
    node_inserted = False
    found_beams: set[str] = set()
    for line in text.split("\n"):
        source, comment = _split_command_comment(line)
        indentation = source[: len(source) - len(source.lstrip())]
        try:
            tokens = shlex.split(source)
        except ValueError as error:
            raise ValueError(
                f"Cannot split a script with invalid quoting: {error}"
            ) from error

        if len(tokens) >= 4 and tokens[0] == "beam" and tokens[1] in splits:
            beam_id = tokens[1]
            if not node_inserted:
                transformed_lines.append(node_command)
                node_inserted = True
            if beam_id in found_beams:
                raise ValueError(f"Beam command {beam_id!r} occurs more than once")
            found_beams.add(beam_id)
            left_id, right_id, _, _ = splits[beam_id]
            left_tokens = [tokens[0], left_id, tokens[2], node_id, *tokens[4:]]
            right_tokens = [tokens[0], right_id, node_id, tokens[3], *tokens[4:]]
            transformed_lines.append(_script_line(left_tokens, indentation, comment))
            transformed_lines.append(_script_line(right_tokens, indentation))
            continue

        if (
            len(tokens) >= 4
            and tokens[0] == "load"
            and tokens[1] == "distributed"
            and tokens[2] in splits
        ):
            beam_id = tokens[2]
            left_id, right_id, split_position, beam_length = splits[beam_id]
            options = _required(
                _parse_options(tokens[3:]),
                (
                    "direction",
                    "value_start",
                    "value_end",
                    "position_start",
                    "position_end",
                    "case",
                ),
            )
            value_start = _number(options["value_start"], "value_start")
            value_end = _number(options["value_end"], "value_end")
            position_start = _number(options["position_start"], "position_start")
            position_end = _number(options["position_end"], "position_end")
            if position_start > position_end:
                raise ValueError(
                    f"Distributed load on beam {beam_id!r} has reversed positions"
                )
            if position_start < 0 or position_end > beam_length:
                if (
                    position_start < -_BEAM_SPLIT_TOLERANCE
                    or position_end > beam_length + _BEAM_SPLIT_TOLERANCE
                ):
                    raise ValueError(
                        f"Distributed load on beam {beam_id!r} extends beyond its length"
                    )
                original_start = position_start
                original_end = position_end
                position_start = max(0.0, position_start)
                position_end = min(beam_length, position_end)
                if original_end > original_start:
                    value_start, value_end = (
                        value_start
                        + (value_end - value_start)
                        * (position_start - original_start)
                        / (original_end - original_start),
                        value_start
                        + (value_end - value_start)
                        * (position_end - original_start)
                        / (original_end - original_start),
                    )

            def updated_load(
                source_tokens: list[str],
                target_id: str,
                start_position: float,
                end_position: float,
                start_value: float = value_start,
                end_value: float = value_end,
            ) -> list[str]:
                load_tokens = source_tokens.copy()
                load_tokens[2] = target_id
                replacements = {
                    "position_start": format(start_position, ".15g"),
                    "position_end": format(end_position, ".15g"),
                    "value_start": format(start_value, ".15g"),
                    "value_end": format(end_value, ".15g"),
                }
                for index in range(3, len(load_tokens)):
                    key, separator, _ = load_tokens[index].partition("=")
                    if separator and key in replacements:
                        load_tokens[index] = f"{key}={replacements[key]}"
                return load_tokens

            if position_end <= split_position:
                transformed_lines.append(
                    _script_line(
                        updated_load(tokens, left_id, position_start, position_end),
                        indentation,
                        comment,
                    )
                )
            elif position_start >= split_position:
                transformed_lines.append(
                    _script_line(
                        updated_load(
                            tokens,
                            right_id,
                            max(0.0, position_start - split_position),
                            max(0.0, position_end - split_position),
                        ),
                        indentation,
                        comment,
                    )
                )
            else:
                value_at_split = value_start + (value_end - value_start) * (
                    (split_position - position_start) / (position_end - position_start)
                )
                transformed_lines.append(
                    _script_line(
                        updated_load(
                            tokens,
                            left_id,
                            position_start,
                            split_position,
                            value_start,
                            value_at_split,
                        ),
                        indentation,
                        comment,
                    )
                )
                transformed_lines.append(
                    _script_line(
                        updated_load(
                            tokens,
                            right_id,
                            0.0,
                            position_end - split_position,
                            value_at_split,
                            value_end,
                        ),
                        indentation,
                    )
                )
            continue

        transformed_lines.append(line)

    if found_beams != set(beam_ids):
        missing = sorted(set(beam_ids) - found_beams)
        raise ValueError(f"No command found for beam(s): {', '.join(missing)}")
    transformed = "\n".join(transformed_lines)
    compile_commands(transformed)
    return transformed


def delete_support_from_script(text: str, node_id: str) -> str:
    """Remove the support command attached to a node."""
    model = compile_commands(text)
    supports = model.get("supports")
    if not isinstance(supports, list) or not any(
        isinstance(support, dict) and support.get("node") == node_id
        for support in supports
    ):
        raise ValueError(f"No support found at node {node_id!r}")

    remaining_lines: list[str] = []
    for line in text.split("\n"):
        source, _ = _split_command_comment(line)
        tokens = shlex.split(source)
        if len(tokens) >= 2 and tokens[0] == "support" and tokens[1] == node_id:
            continue
        remaining_lines.append(line)
    result = "\n".join(remaining_lines)
    compile_commands(result)
    return result


def delete_node_from_script(text: str, node_id: str) -> str:
    """Remove a node, its connected beams, their loads, and attached support."""
    model = compile_commands(text)
    nodes = model.get("nodes")
    beams = model.get("beams")
    if not isinstance(nodes, list) or not isinstance(beams, list):
        raise TypeError("Model nodes and beams must be lists")
    if not any(isinstance(node, dict) and node.get("id") == node_id for node in nodes):
        raise ValueError(f"Node {node_id!r} not found")

    deleted_beam_ids = {
        beam["id"]
        for beam in beams
        if isinstance(beam, dict)
        and isinstance(beam.get("id"), str)
        and node_id in (beam.get("node_start"), beam.get("node_end"))
    }
    remaining_lines: list[str] = []
    for line in text.split("\n"):
        source, _ = _split_command_comment(line)
        tokens = shlex.split(source)
        if len(tokens) >= 2 and tokens[0] == "node" and tokens[1] == node_id:
            continue
        if len(tokens) >= 2 and tokens[0] == "support" and tokens[1] == node_id:
            continue
        if len(tokens) >= 4 and tokens[0] == "beam" and tokens[1] in deleted_beam_ids:
            continue
        if (
            len(tokens) >= 3
            and tokens[0] == "load"
            and tokens[1] == "distributed"
            and tokens[2] in deleted_beam_ids
        ):
            continue
        remaining_lines.append(line)
    result = "\n".join(remaining_lines)
    compile_commands(result)
    return result


def _record(
    records: list[dict[str, object]], record: dict[str, object], id_key: str = "id"
) -> None:
    if any(item.get(id_key) == record.get(id_key) for item in records):
        raise ValueError(f"Duplicate identifier {record[id_key]!r}")
    records.append(record)


class CommandScript:
    """Build a model by replaying the commands in a MyFEM script."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {
            "format_version": FORMAT_VERSION,
            "units": "SI",
            "dimension": 2,
        }
        self._materials: list[dict[str, object]] = []
        self._sections: list[dict[str, object]] = []
        self._nodes: list[dict[str, object]] = []
        self._beams: list[dict[str, object]] = []
        self._supports: list[dict[str, object]] = []
        self._loads: list[dict[str, object]] = []
        self._load_combinations: list[dict[str, object]] = []
        self._precision: dict[str, object] | None = None
        self._precision_options: set[str] = set()
        self._model_declared = False

    def execute(self, line: str) -> None:
        """Execute one command line."""
        tokens = shlex.split(line, comments=True)
        if not tokens:
            return

        command, *args = tokens
        if command == "model":
            self._model(args)
        elif command == "material":
            self._material(args)
        elif command == "section":
            self._section(args)
        elif command == "node":
            self._node(args)
        elif command == "beam":
            self._beam(args)
        elif command == "support":
            self._support(args)
        elif command == "load":
            self._load(args)
        elif command == "combination":
            self._combination(args)
        elif command == "precision":
            self._set_precision(args)
        else:
            raise ValueError(f"Unknown command {command!r}")

    def _model(self, args: list[str]) -> None:
        expected = ["2D", "xz", "x=right", "z=down"]
        if args != expected:
            raise ValueError("model syntax: model 2D xz x=right z=down")
        if self._model_declared:
            raise ValueError("The model declaration may only appear once")
        self._model_declared = True

    def _material(self, args: list[str]) -> None:
        if not args:
            raise ValueError("material requires an identifier")
        options = _required(_parse_options(args[1:]), ("E", "G", "nu", "rho"))
        material: dict[str, object] = {"id": args[0]}
        material.update(
            {key: _number(options[key], key) for key in ("E", "G", "nu", "rho")}
        )
        _record(self._materials, material)

    def _section(self, args: list[str]) -> None:
        if not args:
            raise ValueError("section requires an identifier")
        options = _required(_parse_options(args[1:]), ("A", "I_yy", "I_zz", "I_T"))
        section: dict[str, object] = {"id": args[0]}
        section.update(
            {key: _number(options[key], key) for key in ("A", "I_yy", "I_zz", "I_T")}
        )
        _record(self._sections, section)

    def _node(self, args: list[str]) -> None:
        if not args:
            raise ValueError("node requires an identifier")
        options = _required(_parse_options(args[1:]), ("x", "z"), ("y",))
        node: dict[str, object] = {"id": args[0]}
        node["x"] = _number(options["x"], "x")
        node["y"] = _number(options.get("y", 0.0), "y")
        node["z"] = _number(options["z"], "z")
        _record(self._nodes, node)

    def _beam(self, args: list[str]) -> None:
        if len(args) < 3:
            raise ValueError("beam syntax: beam ID NODE_START NODE_END key=value...")
        options = _required(_parse_options(args[3:]), (), ("material", "section"))
        node_start = self._find(self._nodes, args[1], "node")
        node_end = self._find(self._nodes, args[2], "node")
        start = tuple(_number(node_start[axis], axis) for axis in ("x", "y", "z"))
        end = tuple(_number(node_end[axis], axis) for axis in ("x", "y", "z"))
        length = math.dist(start, end)
        if length == 0:
            raise ValueError("Beam endpoints must be different")
        material = _identifier(options.get("material", "default"), "material")
        section = _identifier(options.get("section", "default"), "section")
        material_is_default = material == "default"
        section_is_default = section == "default"
        material = self._resolve_property(
            self._materials, material, "material", _DEFAULT_MATERIAL
        )
        section = self._resolve_property(
            self._sections, section, "section", _DEFAULT_SECTION
        )
        beam = {
            "id": args[0],
            "node_start": args[1],
            "node_end": args[2],
            "length": length,
            "material": material,
            "section": section,
        }
        if material_is_default:
            beam["material_was_default"] = True
        if section_is_default:
            beam["section_was_default"] = True
        _record(self._beams, beam)

    def _support(self, args: list[str]) -> None:
        if not args:
            raise ValueError("support requires a node identifier")
        options = _required(
            _parse_options(args[1:]), ("DX", "DZ", "RY"), ("DY", "RX", "RZ")
        )
        self._find(self._nodes, args[0], "node")
        dofs = {
            key: options.get(key, True) for key in ("DX", "DY", "DZ", "RX", "RY", "RZ")
        }
        if any(not isinstance(value, bool) for value in dofs.values()):
            raise ValueError("Support options must be true or false")
        support = {"node": args[0], **dofs}
        _record(self._supports, support, "node")

    def _load(self, args: list[str]) -> None:
        if len(args) < 2 or args[0] != "distributed":
            raise ValueError("load syntax: load distributed BEAM key=value...")
        options = _required(
            _parse_options(args[2:]),
            (
                "direction",
                "value_start",
                "value_end",
                "position_start",
                "position_end",
                "case",
            ),
        )
        self._find(self._beams, args[1], "beam")
        direction = _identifier(options["direction"], "direction")
        case = _identifier(options["case"], "case")
        load: dict[str, object] = {
            "type": "beam_distributed",
            "beam": args[1],
            "direction": direction,
        }
        for key in ("value_start", "value_end", "position_start", "position_end"):
            load[key] = _number(options[key], key)
        load["case"] = case
        self._loads.append(load)

    def _combination(self, args: list[str]) -> None:
        if not args:
            raise ValueError("combination requires an identifier")
        cases = _parse_options(args[1:])
        if not cases:
            raise ValueError("combination requires at least one load case factor")
        if any(not isinstance(value, float) for value in cases.values()):
            raise ValueError("Load combination factors must be numbers")
        combination = {"id": args[0], "cases": cases}
        _record(self._load_combinations, combination)

    def _set_precision(self, args: list[str]) -> None:
        options = _required(_parse_options(args), (), ("absolute", "relative"))
        if not options:
            raise ValueError("precision requires absolute= and/or relative=")
        duplicates = self._precision_options.intersection(options)
        if duplicates:
            raise ValueError(
                f"Precision option(s) specified more than once: "
                f"{', '.join(sorted(duplicates))}"
            )

        if self._precision is None:
            self._precision = {
                "absolute": 0.0,
                "relative": 1e-12,
                "defaulted": False,
            }
        for key, value in options.items():
            number = _number(value, key)
            if number < 0:
                raise ValueError(f"Precision option {key!r} must not be negative")
            self._precision[key] = number
        self._precision_options.update(options)

    @classmethod
    def _resolve_property(
        cls,
        records: list[dict[str, object]],
        identifier: str,
        kind: str,
        fallback: dict[str, float],
    ) -> str:
        if identifier != "default":
            cls._find(records, identifier, kind)
            return identifier

        if any(record.get("id") == "default" for record in records):
            return "default"
        if not records:
            _record(
                records,
                {"id": "default", **fallback, "auto_generated": True},
            )
            return "default"
        if len(records) == 1:
            return _identifier(records[0]["id"], kind)
        raise ValueError(
            f"No {kind} named 'default' exists; {len(records)} different "
            f"{kind}s are defined, so the default is ambiguous"
        )

    @staticmethod
    def _find(
        records: list[dict[str, object]], identifier: str, kind: str
    ) -> dict[str, object]:
        for record in records:
            if record.get("id") == identifier:
                return record
        raise ValueError(f"Unknown {kind} {identifier!r}")

    def to_dict(self) -> dict[str, object]:
        """Return the model data generated by the commands."""
        combinations = self._load_combinations
        if not combinations:
            load_cases = {str(load["case"]) for load in self._loads}
            other_cases = sorted(load_cases - {"default"})
            if other_cases:
                raise ValueError(
                    "No load combination is defined. The default SLS "
                    "combination can only be generated for load case 'default'; "
                    f"found: {', '.join(other_cases)}"
                )
            combinations = [
                {
                    "id": "SLS",
                    "cases": {"default": 1.0},
                    "generated_default": True,
                }
            ]
        return {
            **self._data,
            "materials": self._materials,
            "sections": self._sections,
            "nodes": self._nodes,
            "beams": self._beams,
            "supports": self._supports,
            "loads": self._loads,
            "load_combinations": combinations,
            "precision": self._precision
            or {"absolute": 0.0, "relative": 1e-12, "defaulted": True},
        }


def compile_commands(text: str, source_name: str = "<commands>") -> dict[str, object]:
    """Compile command text into a MyFEM model dictionary."""
    script = CommandScript()
    for line_number, line in enumerate(text.splitlines(), 1):
        try:
            script.execute(line)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{source_name}:{line_number}: {error}") from error
    try:
        return script.to_dict()
    except (TypeError, ValueError) as error:
        raise ValueError(f"{source_name}: {error}") from error


def compile_script(source: Path) -> dict[str, object]:
    """Compile a command script file into a MyFEM model dictionary."""
    return compile_commands(source.read_text(encoding="utf-8"), source_name=str(source))


def write_commands(text: str, destination: Path) -> None:
    """Compile command text and write its model as UTF-8 JSON."""
    _write_model_data(compile_commands(text), destination)


def _write_model_data(data: dict[str, object], destination: Path) -> None:
    destination.write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def write_model(source: Path, destination: Path) -> None:
    """Compile a command script and write its model as UTF-8 JSON."""
    _write_model_data(compile_script(source), destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="MyFEM command script to compile")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="Output JSON path (defaults to the script path with a .json suffix)",
    )
    args = parser.parse_args()
    output = args.output or args.script.with_suffix(".json")
    try:
        write_model(args.script, output)
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
