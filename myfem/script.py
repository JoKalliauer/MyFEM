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

"""Compile MyFEM command scripts into deterministic JSON model files."""

import argparse
import json
import math
import shlex
from pathlib import Path

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
            "format_version": 0.1,
            "units": "SI",
            "dimension": 2,
        }
        self._materials: list[dict[str, object]] = []
        self._sections: list[dict[str, object]] = []
        self._nodes: list[dict[str, object]] = []
        self._members: list[dict[str, object]] = []
        self._supports: list[dict[str, object]] = []
        self._loads: list[dict[str, object]] = []
        self._load_combinations: list[dict[str, object]] = []
        self._precision: dict[str, object] | None = None
        self._precision_options: set[str] = set()

    def execute(self, line: str) -> None:
        """Execute one command line."""
        tokens = shlex.split(line, comments=True)
        if not tokens:
            return

        command, *args = tokens
        if command == "material":
            self._material(args)
        elif command == "section":
            self._section(args)
        elif command == "node":
            self._node(args)
        elif command == "member":
            self._member(args)
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
        options = _required(_parse_options(args[1:]), ("x", "y", "z"))
        node: dict[str, object] = {"id": args[0]}
        node.update({key: _number(options[key], key) for key in ("x", "y", "z")})
        _record(self._nodes, node)

    def _member(self, args: list[str]) -> None:
        if len(args) < 3:
            raise ValueError(
                "member syntax: member ID NODE_START NODE_END key=value..."
            )
        options = _required(_parse_options(args[3:]), (), ("material", "section"))
        node_start = self._find(self._nodes, args[1], "node")
        node_end = self._find(self._nodes, args[2], "node")
        start = tuple(_number(node_start[axis], axis) for axis in ("x", "y", "z"))
        end = tuple(_number(node_end[axis], axis) for axis in ("x", "y", "z"))
        length = math.dist(start, end)
        if length == 0:
            raise ValueError("Member endpoints must be different")
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
        member = {
            "id": args[0],
            "node_start": args[1],
            "node_end": args[2],
            "length": length,
            "material": material,
            "section": section,
        }
        if material_is_default:
            member["material_was_default"] = True
        if section_is_default:
            member["section_was_default"] = True
        _record(self._members, member)

    def _support(self, args: list[str]) -> None:
        if not args:
            raise ValueError("support requires a node identifier")
        options = _required(
            _parse_options(args[1:]), ("DX", "DY", "DZ", "RX", "RY", "RZ")
        )
        self._find(self._nodes, args[0], "node")
        if any(not isinstance(value, bool) for value in options.values()):
            raise ValueError("Support options must be true or false")
        support = {"node": args[0], **options}
        _record(self._supports, support, "node")

    def _load(self, args: list[str]) -> None:
        if len(args) < 2 or args[0] != "distributed":
            raise ValueError("load syntax: load distributed MEMBER key=value...")
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
        self._find(self._members, args[1], "member")
        direction = _identifier(options["direction"], "direction")
        case = _identifier(options["case"], "case")
        load: dict[str, object] = {
            "type": "member_distributed",
            "member": args[1],
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
            "members": self._members,
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
