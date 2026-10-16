"""Opt-in diagnostic screenshot capture. Nothing is retained by default."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from rox_overlay.app import _resource_root
from rox_overlay.capture.fallback import MssCaptureSource
from rox_overlay.capture.windows import Win32WindowDiscovery, normalize_window_title
from rox_overlay.recognition.panel import PanelDetector
from rox_overlay.recognition.pipeline import RecognitionPipeline
from rox_overlay.recognition.stability import RecognizedState
from rox_overlay.recognition.tesseract import TesseractOcrEngine


def write_diagnostic(
    frame: np.ndarray,
    reading: RecognizedState | None,
    output: str | Path,
    *,
    confirmed: bool,
) -> tuple[Path, Path] | None:
    """Write a screenshot and minimal metadata only after explicit confirmation."""
    image_path = Path(output)
    metadata_path = image_path.with_suffix(".json")
    if not confirmed:
        return None
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(image_path), frame):
        raise OSError(f"não foi possível gravar {image_path}")
    if reading is None:
        payload: dict[str, object] = {"recognized": False}
    else:
        payload = {
            "confidence": reading.confidence,
            "item_type": reading.item_type.value,
            "level": reading.level,
            "panel_rect": {
                "height": reading.panel_rect.height,
                "width": reading.panel_rect.width,
                "x": reading.panel_rect.x,
                "y": reading.panel_rect.y,
            },
            "progress": reading.progress,
        }
    try:
        metadata_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        image_path.unlink(missing_ok=True)
        raise
    return image_path, metadata_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera uma captura diagnóstica local somente com consentimento explícito."
    )
    parser.add_argument("--window-title", required=True, help="título, ou parte do título, da janela")
    parser.add_argument("--output", required=True, type=Path, help="caminho explícito do PNG")
    parser.add_argument(
        "--confirm-save",
        action="store_true",
        help="confirma que a imagem da janela poderá conter informações privadas",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    wanted = normalize_window_title(args.window_title)
    discovery = Win32WindowDiscovery()
    window = next(
        (item for item in discovery.list_windows() if wanted in normalize_window_title(item.title)),
        None,
    )
    if window is None:
        raise SystemExit("Janela não encontrada.")
    frame = MssCaptureSource().capture(window)
    if frame is None:
        raise SystemExit("Não foi possível capturar a janela.")
    root = _resource_root()
    engine = TesseractOcrEngine(
        root / "vendor" / "tesseract" / "tesseract.exe",
        root / "vendor" / "tesseract" / "tessdata",
    )
    reading = RecognitionPipeline(PanelDetector(), engine).recognize(frame)
    if not args.confirm_save:
        print("Nada foi salvo. Repita com --confirm-save após revisar o caminho e o aviso de privacidade.")
        return 2
    written = write_diagnostic(frame, reading, args.output, confirmed=True)
    assert written is not None
    print(f"Captura: {written[0]}\nMetadados: {written[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
