# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-24

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-24 23:39 CET: Copilot: Defines shared application and model version rules

"""Shared MyFEM application and model-format version handling."""

import re
from datetime import datetime

FORMAT_BASE_VERSION = "0.2"
FORMAT_VERSION = "0.2.2026-11-24_23-39"

_CANONICAL_VERSION_PATTERN = re.compile(
    r"(?P<base>\d+\.\d+)"
    r"(?:\.(?P<year>\d{4})"
    r"(?:-(?P<month>\d{2})"
    r"(?:-(?P<day>\d{2})"
    r"(?:_(?P<hour>\d{2})"
    r"(?:-(?P<minute>\d{2}))?)?)?)?)?"
)
_PACKAGE_VERSION_PATTERN = re.compile(
    r"(?P<base>\d+\.\d+)"
    r"(?:\.(?P<year>\d{4})"
    r"(?:\.(?P<month>\d{2})"
    r"(?:\.(?P<day>\d{2})"
    r"(?:\.(?P<hour>\d{2})"
    r"(?:\.(?P<minute>\d{2}))?)?)?)?)?"
)


def _date_components_are_valid(match: re.Match[str]) -> bool:
    year = match.group("year")
    if year is None:
        return True

    month = match.group("month")
    day = match.group("day")
    hour = match.group("hour")
    minute = match.group("minute")
    try:
        datetime(
            int(year),
            int(month or 1),
            int(day or 1),
            int(hour or 0),
            int(minute or 0),
        )
    except ValueError:
        return False
    return True


def is_compatible_format_version(value: object) -> bool:
    """Return whether a model version belongs to the current 0.2 format family."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 0.2
    if not isinstance(value, str):
        return False

    match = _CANONICAL_VERSION_PATTERN.fullmatch(value)
    return (
        match is not None
        and match.group("base") == FORMAT_BASE_VERSION
        and _date_components_are_valid(match)
    )


def format_package_version(value: str) -> str:
    """Display a PEP 440 dotted date version using MyFEM's canonical notation."""
    match = _PACKAGE_VERSION_PATTERN.fullmatch(value)
    if (
        match is None
        or match.group("base") != FORMAT_BASE_VERSION
        or not _date_components_are_valid(match)
    ):
        raise ValueError(
            f"MyFEM package version {value!r} must use the {FORMAT_BASE_VERSION} "
            "base and a valid date suffix"
        )

    displayed = match.group("base")
    for name, separator in (
        ("year", "."),
        ("month", "-"),
        ("day", "-"),
        ("hour", "_"),
        ("minute", "-"),
    ):
        component = match.group(name)
        if component is None:
            break
        displayed += separator + component
    return displayed
