"""Pure enchantment requirements and cost calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class ItemType(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"


@dataclass(frozen=True)
class EnchantRequirement:
    current_level: int
    next_level: int
    points: int


@dataclass(frozen=True)
class CostEstimate:
    item_type: ItemType
    current_level: int
    next_level: int | None
    progress: float
    remaining_points: int
    remaining_taps: int
    remaining_muspellium: int
    remaining_zeny: int
    is_max_level: bool


_POINTS_BY_LEVEL = {
    1: 10,
    2: 30,
    3: 60,
    4: 100,
    5: 150,
    6: 250,
    7: 400,
    8: 600,
    9: 850,
    10: 1_150,
    11: 1_550,
    12: 2_050,
    13: 2_800,
    14: 3_800,
    15: 5_050,
    16: 6_550,
    17: 8_300,
    18: 10_300,
    19: 12_550,
}

_POINTS_PER_TAP = {
    ItemType.WEAPON: 3,
    ItemType.ARMOR: 1,
    ItemType.ACCESSORY: 1,
}

_MUSPELLIUM_PER_TAP = {
    ItemType.WEAPON: 90,
    ItemType.ARMOR: 30,
    ItemType.ACCESSORY: 30,
}


def _validate_level(level: int) -> None:
    if isinstance(level, bool) or not isinstance(level, int):
        raise TypeError("level must be an integer")
    if not 1 <= level <= 20:
        raise ValueError("level must be between 1 and 20")


def requirement_for(level: int) -> EnchantRequirement | None:
    _validate_level(level)
    if level == 20:
        return None
    return EnchantRequirement(level, level + 1, _POINTS_BY_LEVEL[level])


def estimate_cost(
    item_type: ItemType,
    level: int,
    progress: float,
    unit_price: int,
) -> CostEstimate:
    if not isinstance(item_type, ItemType):
        raise TypeError("item_type must be an ItemType")
    _validate_level(level)
    if isinstance(progress, bool) or not isinstance(progress, (int, float)):
        raise TypeError("progress must be a number")
    if not 0 <= progress <= 1:
        raise ValueError("progress must be between 0 and 1")
    if isinstance(unit_price, bool) or not isinstance(unit_price, int):
        raise TypeError("unit_price must be an integer")
    if unit_price < 0:
        raise ValueError("unit_price must be non-negative")

    requirement = requirement_for(level)
    if requirement is None:
        return CostEstimate(
            item_type=item_type,
            current_level=level,
            next_level=None,
            progress=float(progress),
            remaining_points=0,
            remaining_taps=0,
            remaining_muspellium=0,
            remaining_zeny=0,
            is_max_level=True,
        )

    points_per_tap = _POINTS_PER_TAP[item_type]
    if progress >= 1:
        earned_points = requirement.points
    else:
        estimated_taps = (requirement.points * float(progress)) / points_per_tap
        earned_taps = math.floor(estimated_taps + 0.5)
        earned_points = min(earned_taps * points_per_tap, requirement.points)

    remaining_points = max(0, requirement.points - earned_points)
    remaining_taps = math.ceil(remaining_points / points_per_tap)
    remaining_muspellium = remaining_taps * _MUSPELLIUM_PER_TAP[item_type]

    return CostEstimate(
        item_type=item_type,
        current_level=level,
        next_level=requirement.next_level,
        progress=float(progress),
        remaining_points=remaining_points,
        remaining_taps=remaining_taps,
        remaining_muspellium=remaining_muspellium,
        remaining_zeny=remaining_muspellium * unit_price,
        is_max_level=False,
    )
