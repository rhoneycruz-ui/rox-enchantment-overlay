from __future__ import annotations

import json
from pathlib import Path

import pytest

from rox_overlay.config import AppConfig, ConfigStore


CONFIG_PATH = Path("work/test-user-config.json")


def setup_function() -> None:
    CONFIG_PATH.unlink(missing_ok=True)
    CONFIG_PATH.with_suffix(".tmp").unlink(missing_ok=True)


def test_defaults_match_product_design() -> None:
    assert AppConfig() == AppConfig(unit_price=0, opacity_percent=82)


@pytest.mark.parametrize("opacity", [24, 101])
def test_rejects_opacity_outside_supported_range(opacity: int) -> None:
    with pytest.raises(ValueError):
        AppConfig(opacity_percent=opacity)


@pytest.mark.parametrize("price", [-1, 1.5, True])
def test_rejects_invalid_unit_price(price: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        AppConfig(unit_price=price)  # type: ignore[arg-type]


def test_corrupt_json_falls_back_to_defaults() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text("{broken", encoding="utf-8")
    assert ConfigStore(CONFIG_PATH).load() == AppConfig()


def test_round_trips_valid_configuration_atomically() -> None:
    store = ConfigStore(CONFIG_PATH)
    config = AppConfig(456, 35, "Ragnarok X", 4, -2)
    store.save(config)

    assert store.load() == config
    assert not CONFIG_PATH.with_suffix(".tmp").exists()
    assert json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["opacity_percent"] == 35

