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



def test_unknown_and_invalid_fields_do_not_wipe_valid_preferences() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps({"unit_price": 321, "opacity_percent": 7, "future_option": True, "hotkey": "F4"}),
        encoding="utf-8",
    )

    config = ConfigStore(CONFIG_PATH).load()

    assert config.unit_price == 321
    assert config.opacity_percent == AppConfig().opacity_percent
    assert config.hotkey == "F4"


@pytest.mark.parametrize(
    "changes",
    [{"hotkey": "F13"}, {"target_level": 1}, {"target_level": 21}, {"offset_x": 5000}, {"auto_start": 1}],
)
def test_rejects_invalid_new_preferences(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        AppConfig(**changes)  # type: ignore[arg-type]


def test_migrates_from_legacy_file_without_ever_writing_it() -> None:
    legacy = Path("work/legacy-config.json")
    current = Path("work/settings-v1.1.json")
    current.unlink(missing_ok=True)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    original = '{"unit_price": 78, "opacity_percent": 64, "window_title_hint": "Ragnarok X"}\n'
    legacy.write_text(original, encoding="utf-8")
    store = ConfigStore(current, legacy_path=legacy)

    loaded = store.load()
    store.save(loaded)

    assert loaded.unit_price == 78 and loaded.opacity_percent == 64
    assert legacy.read_text(encoding="utf-8") == original
    assert json.loads(current.read_text(encoding="utf-8"))["hotkey"] == "F1"


def test_default_paths_keep_v1_and_v11_settings_apart() -> None:
    from rox_overlay.config import default_config_path, legacy_config_path

    assert default_config_path() != legacy_config_path()
    assert legacy_config_path().name == "config.json"


def test_city_is_saved_and_unknown_city_falls_back_to_prontera(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "settings.json")
    store.save(AppConfig(city="Morroc"))
    assert store.load().city == "Morroc"

    (tmp_path / "settings.json").write_text(json.dumps({"unit_price": 90, "city": "Lutie"}), encoding="utf-8")
    loaded = store.load()
    assert loaded.city == "Prontera"
    assert loaded.unit_price == 90
