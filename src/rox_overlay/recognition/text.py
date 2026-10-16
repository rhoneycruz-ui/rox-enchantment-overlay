"""OCR preprocessing and conservative title/level parsing."""

from __future__ import annotations

import re
import unicodedata

import cv2
import numpy as np

from rox_overlay.domain import ItemType

from .models import FieldReading, OcrEngine


_TYPE_TOKENS = {
    ItemType.ACCESSORY: {"acessorio", "accessory"},
    ItemType.ARMOR: {"armadura", "armor", "armour"},
    ItemType.WEAPON: {"arma", "weapon"},
}


def normalize_ocr_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-z0-9]+", " ", without_accents.casefold()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return re.sub(r"\bnivei\b", "nivel", normalized)


def classify_item_type(text: str) -> ItemType | None:
    tokens = set(normalize_ocr_text(text).split())
    matches = [item_type for item_type, keywords in _TYPE_TOKENS.items() if tokens & keywords]
    return matches[0] if len(matches) == 1 else None


def _prepare_for_ocr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 2:
        gray = image
    else:
        raise ValueError("OCR image must be grayscale or BGR")
    enlarged = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(enlarged)


def read_item_type(image: np.ndarray, ocr: OcrEngine) -> FieldReading[ItemType]:
    result = ocr.read_line(
        _prepare_for_ocr(image),
        languages=("por", "eng"),
        digits_only=False,
    )
    raw = result.raw or (result.value or "")
    item_type = classify_item_type(result.value or "")
    if item_type is None:
        return FieldReading(None, 0.0, raw)
    return FieldReading(item_type, result.confidence, raw)


def read_level(image: np.ndarray, ocr: OcrEngine) -> FieldReading[int]:
    result = ocr.read_line(
        _prepare_for_ocr(image),
        languages=("por", "eng"),
        digits_only=True,
    )
    raw = result.raw or (result.value or "")
    candidate = (result.value or "").strip().upper()
    if not re.fullmatch(r"[0-9ILO]+", candidate):
        return FieldReading(None, 0.0, raw)
    candidate = candidate.replace("I", "1").replace("L", "1").replace("O", "0")
    level = int(candidate)
    if not 1 <= level <= 20:
        return FieldReading(None, 0.0, raw)
    return FieldReading(level, result.confidence, raw)
