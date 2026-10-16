"""Shared recognition value objects and protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, runtime_checkable

import numpy as np


T = TypeVar("T")


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class FieldReading(Generic[T]):
    value: T | None
    confidence: float
    raw: str = ""


@runtime_checkable
class OcrEngine(Protocol):
    def read_line(
        self,
        image: np.ndarray,
        *,
        languages: tuple[str, ...],
        digits_only: bool = False,
    ) -> FieldReading[str]: ...

