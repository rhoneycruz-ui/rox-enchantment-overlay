from __future__ import annotations

import json
from pathlib import Path

import cv2
import pytest

from rox_overlay.domain import ItemType
from rox_overlay.recognition.tesseract import OcrConfigurationError, TesseractOcrEngine
from rox_overlay.recognition.text import read_item_type, read_level


ROOT = Path(__file__).parents[2]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "text"
TESSERACT = ROOT / "vendor" / "tesseract" / "tesseract.exe"
TESSDATA = ROOT / "vendor" / "tesseract" / "tessdata"


def test_rejects_missing_tesseract_executable() -> None:
    with pytest.raises(OcrConfigurationError, match="executável"):
        TesseractOcrEngine(ROOT / "missing-tesseract.exe", TESSDATA)


def test_rejects_missing_language_resources() -> None:
    with pytest.raises(OcrConfigurationError, match="eng.traineddata"):
        TesseractOcrEngine(TESSERACT, ROOT / "work" / "missing-tessdata")


def test_reads_portuguese_and_english_title_fixtures() -> None:
    engine = TesseractOcrEngine(TESSERACT, TESSDATA)
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))

    for case in manifest["titles"]:
        image = cv2.imread(str(FIXTURE_DIR / case["file"]))
        result = read_item_type(image, engine)

        assert result.value is ItemType(case["type"]), (case, result)
        assert result.confidence > 0


def test_reads_real_and_synthetic_level_fixtures() -> None:
    engine = TesseractOcrEngine(TESSERACT, TESSDATA)
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))

    for case in manifest["levels"]:
        image = cv2.imread(str(FIXTURE_DIR / case["file"]))
        result = read_level(image, engine)

        assert result.value == case["level"], (case, result)
        assert result.confidence > 0

