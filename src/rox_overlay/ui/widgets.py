"""Small typed helpers for Qt widget lookup."""

from __future__ import annotations

from typing import TypeVar

from PySide6.QtCore import QObject

W = TypeVar("W", bound=QObject)


def child(parent: QObject, kind: type[W], name: str) -> W:
    """``findChild`` that fails loudly instead of returning ``None``."""
    found = parent.findChild(kind, name)
    if found is None:
        raise LookupError(f"widget {name!r} ({kind.__name__}) não encontrado")
    return found
