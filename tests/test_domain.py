from __future__ import annotations

import pytest

from rox_overlay.domain import ItemType, estimate_cost, requirement_for

EXPECTED_POINTS = {
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


@pytest.mark.parametrize(("level", "points"), EXPECTED_POINTS.items())
def test_requirement_table_matches_scraped_values(level: int, points: int) -> None:
    requirement = requirement_for(level)

    assert requirement is not None
    assert requirement.current_level == level
    assert requirement.next_level == level + 1
    assert requirement.points == points


def test_level_20_is_maximum() -> None:
    assert requirement_for(20) is None

    result = estimate_cost(ItemType.ARMOR, level=20, progress=1.0, unit_price=84)

    assert result.is_max_level is True
    assert result.next_level is None
    assert result.remaining_points == 0
    assert result.remaining_stones == 0
    assert result.remaining_crystals == 0


def test_armor_level_14_at_37_percent() -> None:
    result = estimate_cost(ItemType.ARMOR, level=14, progress=0.37, unit_price=84)

    assert result.remaining_points == 2_394
    assert result.remaining_taps == 2_394
    assert result.remaining_stones == 71_820
    assert result.remaining_crystals == 6_032_880


def test_accessory_uses_one_point_taps() -> None:
    result = estimate_cost(ItemType.ACCESSORY, level=1, progress=0.5, unit_price=100)

    assert result.remaining_points == 5
    assert result.remaining_taps == 5
    assert result.remaining_stones == 150
    assert result.remaining_crystals == 15_000


def test_weapon_rounds_remaining_taps_up() -> None:
    result = estimate_cost(ItemType.WEAPON, level=2, progress=0.01, unit_price=84)

    assert result.remaining_points == 30
    assert result.remaining_taps == 10
    assert result.remaining_stones == 900


@pytest.mark.parametrize("level", [0, 21])
def test_rejects_level_outside_supported_range(level: int) -> None:
    with pytest.raises(ValueError, match="level"):
        requirement_for(level)


@pytest.mark.parametrize("progress", [-0.01, 1.01])
def test_rejects_progress_outside_supported_range(progress: float) -> None:
    with pytest.raises(ValueError, match="progress"):
        estimate_cost(ItemType.ARMOR, level=14, progress=progress, unit_price=84)


@pytest.mark.parametrize("unit_price", [-1, 1.5, True])
def test_rejects_invalid_unit_price(unit_price: object) -> None:
    with pytest.raises((TypeError, ValueError), match="unit_price"):
        estimate_cost(ItemType.ARMOR, level=14, progress=0.5, unit_price=unit_price)  # type: ignore[arg-type]


def test_target_level_adds_full_future_levels_rounded_up_per_level() -> None:
    to_next = estimate_cost(ItemType.WEAPON, 1, 0.0, 1)
    to_three = estimate_cost(ItemType.WEAPON, 1, 0.0, 1, target_level=3)

    assert to_next.remaining_taps == 4  # ceil(10 / 3)
    assert to_three.remaining_taps == 4 + 10  # + ceil(30 / 3)
    assert to_three.remaining_points == 40
    assert to_three.next_level == 3
    assert to_three.target_level == 3
    assert to_three.remaining_crystals == to_three.remaining_stones


def test_target_at_or_below_next_level_behaves_like_next_level() -> None:
    plain = estimate_cost(ItemType.ARMOR, 14, 0.5, 10)

    assert estimate_cost(ItemType.ARMOR, 14, 0.5, 10, target_level=15) == plain
    assert estimate_cost(ItemType.ARMOR, 14, 0.5, 10, target_level=3) == plain


def test_partial_progress_is_flagged_as_approximate() -> None:
    assert estimate_cost(ItemType.ARMOR, 14, 0.5, 1).is_approximate
    assert not estimate_cost(ItemType.ARMOR, 14, 0.0, 1).is_approximate


def test_morroc_armor_counts_stones_not_crystals() -> None:
    result = estimate_cost(ItemType.ARMOR, level=15, progress=0.0, unit_price=88, city="Morroc")

    assert result.remaining_points == 5_050
    assert result.remaining_taps == 2_525  # 2 points per tap
    assert result.remaining_stones == 5_050  # 2 stones per tap
    assert result.stone_name == "Hardening Enchantment Stone"
    assert result.priced_in_crystals is False
    assert result.remaining_crystals == 0


def test_city_progress_need_not_be_a_multiple_of_points_per_tap() -> None:
    # Glast Heim weapon gives 96 points per tap; half of 5050 is 2525 points left → 27 taps.
    result = estimate_cost(ItemType.WEAPON, level=15, progress=0.5, unit_price=0, city="Glast Heim")

    assert result.remaining_points == 2_525
    assert result.remaining_taps == 27
    assert result.remaining_stones == 27 * 6


def test_rejects_unknown_city() -> None:
    with pytest.raises(ValueError, match="city"):
        estimate_cost(ItemType.ARMOR, level=1, progress=0.0, unit_price=0, city="Lutie")
