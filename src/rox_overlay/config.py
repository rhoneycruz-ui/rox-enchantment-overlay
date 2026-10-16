"""Validated user preferences stored locally as JSON."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    unit_price: int = 0
    opacity_percent: int = 82
    window_title_hint: str = ""
    offset_x: int = 0
    offset_y: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.unit_price, bool) or not isinstance(self.unit_price, int):
            raise TypeError("unit_price must be an integer")
        if self.unit_price < 0:
            raise ValueError("unit_price must be non-negative")
        if isinstance(self.opacity_percent, bool) or not isinstance(self.opacity_percent, int):
            raise TypeError("opacity_percent must be an integer")
        if not 25 <= self.opacity_percent <= 100:
            raise ValueError("opacity_percent must be between 25 and 100")


def default_config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return base / "ROX Enchantment Overlay" / "config.json"


class ConfigStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_config_path()

    def load(self) -> AppConfig:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return AppConfig(**payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return AppConfig()

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

