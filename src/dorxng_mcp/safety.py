"""Hard safety checks for DorXNG MCP inputs."""

from __future__ import annotations

import re
from typing import Iterable

# Hard block only for illegal sexual material involving minors.  Keep this
# focused: the intent is to prevent the MCP from searching for, surfacing, or
# storing such material, not to police ordinary red-team/pentest dorking.
_MINOR_TERMS = re.compile(
    r"\b(child|children|minor|minors|underage|teen|teens|preteen|preteens|kid|kids|infant|toddler|schoolgirl|schoolboy)\b",
    re.IGNORECASE,
)
_SEXUAL_MATERIAL_TERMS = re.compile(
    r"\b(porn|porno|pornography|nude|nudes|sex|sexual|explicit|erotic|abuse|exploitation|molest|molestation|csam|cp)\b",
    re.IGNORECASE,
)


def assert_no_illegal_sexual_material(*values: object) -> None:
    """Raise ValueError when inputs indicate illegal sexual material involving minors."""
    text = _flatten(values)
    if _MINOR_TERMS.search(text) and _SEXUAL_MATERIAL_TERMS.search(text):
        raise ValueError(
            "blocked: this MCP will not search for, provide guidance for, access, download, or store illegal sexual material involving minors"
        )


def _flatten(values: Iterable[object]) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            parts.append(_flatten(value.keys()))
            parts.append(_flatten(value.values()))
        elif isinstance(value, Iterable):
            parts.append(_flatten(value))
        else:
            parts.append(str(value))
    return " ".join(parts)
