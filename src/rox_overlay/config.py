"""Validated user preferences stored locally as JSON."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from rox_overlay.domain import CITIES, DEFAULT_CITY

logger = logging.getLogger(__name__)

HOTKEY_CHOICES: tuple[str, ...] = tuple(f"F{number}" for number in range(1, 13))
MAX_OVERLAY_OFFSET = 2000


def _require_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _require_bool(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")
    return value


@dataclass(frozen=True)
class AppConfig:
    unit_price: int = 0
    opacity_percent: int = 82
    window_title_hint: str = ""
    offset_x: int = 0
    offset_y: int = 0
    hotkey: str = "F1"
    target_level: int = 0
    auto_start: bool = True
    autoclick_stop_on_level_up: bool = True
    city: str = DEFAULT_CITY
    auto_city: bool = True
    autoclick_enabled: bool = False

    def __post_init__(self) -> None:
        if _require_int("unit_price", self.unit_price) < 0:
            raise ValueError("unit_price must be non-negative")
        if not 25 <= _require_int("opacity_percent", self.opacity_percent) <= 100:
            raise ValueError("opacity_percent must be between 25 and 100")
        if not isinstance(self.window_title_hint, str):
            raise TypeError("window_title_hint must be a string")
        for name in ("offset_x", "offset_y"):
            if abs(_require_int(name, getattr(self, name))) > MAX_OVERLAY_OFFSET:
                raise ValueError(f"{name} must be within ±{MAX_OVERLAY_OFFSET}")
        if self.hotkey not in HOTKEY_CHOICES:
            raise ValueError("hotkey must be one of F1..F12")
        target = _require_int("target_level", self.target_level)
        if target != 0 and not 2 <= target <= 20:
            raise ValueError("target_level must be 0 (next level) or between 2 and 20")
        _require_bool("auto_start", self.auto_start)
        _require_bool("autoclick_stop_on_level_up", self.autoclick_stop_on_level_up)
        _require_bool("auto_city", self.auto_city)
        _require_bool("autoclick_enabled", self.autoclick_enabled)
        if self.city not in CITIES:
            raise ValueError(f"city must be one of {', '.join(CITIES)}")


def app_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return base / "ROX Enchantment Overlay"


def default_config_path() -> Path:
    # v1.1 keeps its own file: v1.0 rejects unknown keys and would reset itself
    # if both versions shared config.json.
    return app_data_dir() / "settings-v1.1.json"


def legacy_config_path() -> Path:
    """v1.0 settings, read once (never written) to migrate price, opacity, window."""
    return app_data_dir() / "config.json"


def _config_from_payload(payload: dict[str, Any]) -> AppConfig:
    """Keep every valid known field; ignore unknown keys and drop invalid values.

    One bad or future field must never wipe the user's whole configuration.
    """
    known = {field.name for field in fields(AppConfig)}
    accepted: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in known:
            logger.info("ignorando campo desconhecido na configuração: %s", key)
            continue
        try:
            AppConfig(**{**accepted, key: value})
        except (TypeError, ValueError) as exc:
            logger.warning("valor inválido para %s na configuração (%s); usando padrão", key, exc)
            continue
        accepted[key] = value
    return AppConfig(**accepted)


class ConfigStore:
    def __init__(self, path: str | Path | None = None, *, legacy_path: str | Path | None = None) -> None:
        if path is None:
            self.path = default_config_path()
            self.legacy_path: Path | None = Path(legacy_path) if legacy_path is not None else legacy_config_path()
        else:
            self.path = Path(path)
            self.legacy_path = Path(legacy_path) if legacy_path is not None else None

    def load(self) -> AppConfig:
        source = self.path
        if not source.exists() and self.legacy_path is not None and self.legacy_path.exists():
            logger.info("importando preferências da versão anterior de %s", self.legacy_path)
            source = self.legacy_path
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return AppConfig()
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("configuração ilegível em %s (%s); usando padrões", self.path, exc)
            return AppConfig()
        if not isinstance(payload, dict):
            logger.warning("configuração em formato inesperado; usando padrões")
            return AppConfig()
        return _config_from_payload(payload)

    def save(self, config: AppConfig) -> None:
        if not isinstance(config, AppConfig):
            raise TypeError("config must be an AppConfig")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
