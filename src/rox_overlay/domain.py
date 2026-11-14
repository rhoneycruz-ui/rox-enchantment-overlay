"""Pure enchantment requirements and cost calculations.

Game numbers live in ``data/enchant_tables.json`` so a game patch only needs a
data update, not a code change.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


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
    remaining_stones: int
    remaining_crystals: int
    is_max_level: bool
    target_level: int | None = None
    city: str = "Prontera"
    stone_name: str = "Lv.1 Muspellium"
    priced_in_crystals: bool = True

    @property
    def is_approximate(self) -> bool:
        """Progress is read from bar pixels, so partial progress is an estimate."""
        return 0 < self.progress < 1


@dataclass(frozen=True)
class StoneRule:
    stone: str
    stones_per_tap: int
    points_per_tap: int


@dataclass(frozen=True)
class EnchantTables:
    version: str
    max_level: int
    points_by_level: dict[int, int]
    crystal_city: str
    cities: dict[str, dict[ItemType, StoneRule]]


def _load_tables(path: Path | None = None) -> EnchantTables:
    source = path or Path(__file__).parent / "data" / "enchant_tables.json"
    payload: dict[str, Any] = json.loads(source.read_text(encoding="utf-8"))
    max_level = int(payload["max_level"])
    points = {int(level): int(value) for level, value in payload["points_by_level"].items()}
    if sorted(points) != list(range(1, max_level)):
        raise ValueError("points_by_level must cover every level below max_level")
    if any(value <= 0 for value in points.values()):
        raise ValueError("points_by_level values must be positive")
    cities: dict[str, dict[ItemType, StoneRule]] = {}
    for city, items in payload["cities"].items():
        rules = {
            ItemType(kind): StoneRule(str(rule["stone"]), int(rule["stones_per_tap"]), int(rule["points_per_tap"]))
            for kind, rule in items.items()
        }
        if set(rules) != set(ItemType):
            raise ValueError(f"city {city} must cover every item type")
        if any(rule.stones_per_tap <= 0 or rule.points_per_tap <= 0 for rule in rules.values()):
            raise ValueError(f"city {city} has non-positive per-tap values")
        cities[str(city)] = rules
    crystal_city = str(payload["crystal_city"])
    if crystal_city not in cities:
        raise ValueError("crystal_city must be one of the cities")
    return EnchantTables(str(payload.get("game_data_version", "")), max_level, points, crystal_city, cities)


TABLES = _load_tables()
MAX_LEVEL = TABLES.max_level
DEFAULT_CITY = TABLES.crystal_city
CITIES: tuple[str, ...] = tuple(TABLES.cities)


def _validate_level(level: int) -> None:
    if isinstance(level, bool) or not isinstance(level, int):
        raise TypeError("level must be an integer")
    if not 1 <= level <= MAX_LEVEL:
        raise ValueError(f"level must be between 1 and {MAX_LEVEL}")


def requirement_for(level: int) -> EnchantRequirement | None:
    _validate_level(level)
    if level == MAX_LEVEL:
        return None
    return EnchantRequirement(level, level + 1, TABLES.points_by_level[level])


def estimate_cost(
    item_type: ItemType,
    level: int,
    progress: float,
    unit_price: int,
    target_level: int | None = None,
    city: str = DEFAULT_CITY,
) -> CostEstimate:
    """Cost to reach the next level, or ``target_level`` when it is further away.

    Levels after the current one are counted in full; taps are rounded up per
    level, which keeps the estimate on the safe (never-too-low) side. Crystals are
    only priced for the city that consumes Muspellium bought with crystals
    (Prontera); other cities report the number of enchantment stones.
    """
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
    if target_level is not None:
        _validate_level(target_level)

    if city not in TABLES.cities:
        raise ValueError(f"unknown city: {city!r}")
    rule = TABLES.cities[city][item_type]
    priced = city == TABLES.crystal_city

    requirement = requirement_for(level)
    if requirement is None:
        return CostEstimate(
            item_type=item_type,
            current_level=level,
            next_level=None,
            progress=float(progress),
            remaining_points=0,
            remaining_taps=0,
            remaining_stones=0,
            remaining_crystals=0,
            is_max_level=True,
            city=city,
            stone_name=rule.stone,
            priced_in_crystals=priced,
        )

    # Points earned so far are read from the bar. They need not be a multiple
    # of this city's points-per-tap (the player may have used another city).
    earned_points = min(requirement.points, math.floor(requirement.points * float(progress) + 0.5))
    remaining_points = max(0, requirement.points - earned_points)
    remaining_taps = math.ceil(remaining_points / rule.points_per_tap)

    goal = requirement.next_level
    effective_target: int | None = None
    if target_level is not None and target_level > requirement.next_level:
        goal = target_level
        effective_target = target_level
        for future_level in range(requirement.next_level, target_level):
            future_points = TABLES.points_by_level[future_level]
            remaining_points += future_points
            remaining_taps += math.ceil(future_points / rule.points_per_tap)

    remaining_stones = remaining_taps * rule.stones_per_tap

    return CostEstimate(
        item_type=item_type,
        current_level=level,
        next_level=goal,
        progress=float(progress),
        remaining_points=remaining_points,
        remaining_taps=remaining_taps,
        remaining_stones=remaining_stones,
        remaining_crystals=remaining_stones * unit_price if priced else 0,
        is_max_level=False,
        target_level=effective_target,
        city=city,
        stone_name=rule.stone,
        priced_in_crystals=priced,
    )
