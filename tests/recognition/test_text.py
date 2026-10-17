from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from rox_overlay.domain import ItemType
from rox_overlay.recognition.models import FieldReading
from rox_overlay.recognition.text import (
    classify_item_type,
    normalize_ocr_text,
    read_item_type,
    read_level,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Nível da Arma", ItemType.WEAPON),
        ("Nivel da Armadura", ItemType.ARMOR),
        ("NÍVEL DO ACESSÓRIO", ItemType.ACCESSORY),
        ("Weapon Level", ItemType.WEAPON),
        ("Armor Level", ItemType.ARMOR),
        ("Armour Level", ItemType.ARMOR),
        ("Accessory Level", ItemType.ACCESSORY),
        ("NiveI da Arma", ItemType.WEAPON),
        ("~yRfvel da Armadurd~", ItemType.ARMOR),
    ],
)
def test_classifies_portuguese_and_english_titles(text: str, expected: ItemType) -> None:
    assert classify_item_type(text) is expected


def test_normalizes_accents_case_whitespace_and_level_ocr_noise() -> None:
    assert normalize_ocr_text("  NÍVEL   DO  ACESSÓRIO ") == "nivel do acessorio"
    assert normalize_ocr_text("NiveI da Arma") == "nivel da arma"


@pytest.mark.parametrize("text", ["", "Refino", "Nível", "ArmaduraArma"])
def test_unknown_title_is_never_guessed(text: str) -> None:
    assert classify_item_type(text) is None


@dataclass
class FakeOcrEngine:
    result: FieldReading[str]
    last_languages: tuple[str, ...] | None = None
    last_digits_only: bool | None = None
    last_shape: tuple[int, ...] | None = None

    def read_line(
        self,
        image: np.ndarray,
        *,
        languages: tuple[str, ...],
        digits_only: bool = False,
    ) -> FieldReading[str]:
        self.last_languages = languages
        self.last_digits_only = digits_only
        self.last_shape = image.shape
        return self.result


def _sample_image() -> np.ndarray:
    return np.zeros((12, 40, 3), dtype=np.uint8)


def test_reads_item_type_with_bilingual_ocr_and_preserves_confidence() -> None:
    ocr = FakeOcrEngine(FieldReading("Weapon Level", 0.91, "Weapon Level"))

    result = read_item_type(_sample_image(), ocr)

    assert result == FieldReading(ItemType.WEAPON, 0.91, "Weapon Level")
    assert ocr.last_languages == ("por", "eng")
    assert ocr.last_digits_only is False
    assert ocr.last_shape is not None
    assert ocr.last_shape[0] > 12


@pytest.mark.parametrize(("raw", "expected"), [("14", 14), (" 19 ", 19), ("I4", 14)])
def test_reads_supported_level(raw: str, expected: int) -> None:
    ocr = FakeOcrEngine(FieldReading(raw, 0.88, raw))

    result = read_level(_sample_image(), ocr)

    assert result == FieldReading(expected, 0.88, raw)
    assert ocr.last_languages == ("por", "eng")
    assert ocr.last_digits_only is True


@pytest.mark.parametrize("raw", ["21", "", "level fourteen"])
def test_rejects_invalid_level_without_guessing(raw: str) -> None:
    ocr = FakeOcrEngine(FieldReading(raw, 0.95, raw))

    result = read_level(_sample_image(), ocr)

    assert result.value is None
    assert result.confidence == 0
    assert result.raw == raw


def test_rejects_unclassified_item_type_without_preserving_false_confidence() -> None:
    ocr = FakeOcrEngine(FieldReading("Refino", 0.99, "Refino"))

    result = read_item_type(_sample_image(), ocr)

    assert result == FieldReading(None, 0.0, "Refino")
