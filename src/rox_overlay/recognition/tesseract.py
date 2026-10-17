"""Portable subprocess adapter for Tesseract OCR."""

from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np

from .models import FieldReading


class OcrConfigurationError(RuntimeError):
    """Raised when required local OCR resources are unavailable."""


class OcrExecutionError(RuntimeError):
    """Raised when the local OCR process cannot analyze an image."""


class TesseractOcrEngine:
    supports_parallel = True

    def __init__(self, tesseract_path: str | Path, tessdata_dir: str | Path) -> None:
        self._executable = Path(tesseract_path)
        self._tessdata_dir = Path(tessdata_dir)
        if not self._executable.is_file():
            raise OcrConfigurationError("executável do Tesseract não encontrado")
        for language in ("eng", "por"):
            resource = self._tessdata_dir / f"{language}.traineddata"
            if not resource.is_file():
                raise OcrConfigurationError(f"recurso OCR ausente: {resource.name}")

    def read_line(
        self,
        image: np.ndarray,
        *,
        languages: tuple[str, ...],
        digits_only: bool = False,
    ) -> FieldReading[str]:
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            return FieldReading(None, 0.0)

        command = [
            str(self._executable),
            "stdin",
            "stdout",
            "--tessdata-dir",
            str(self._tessdata_dir),
            "-l",
            "+".join(languages),
            "--psm",
            "7",
        ]
        if digits_only:
            command.extend(["-c", "tessedit_char_whitelist=0123456789"])
        try:
            completed = subprocess.run(
                command,
                input=encoded.tobytes(),
                capture_output=True,
                timeout=10,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OcrExecutionError("falha ao executar o OCR local") from exc
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise OcrExecutionError(detail or "Tesseract retornou erro")

        decoded = completed.stdout.decode("utf-8", errors="replace").replace("\f", " ")
        text = " ".join(decoded.split())
        # The bundled, redistributable Tesseract 4 beta does not ship the TSV
        # output config. Keep confidence deliberately conservative; semantic
        # validation and temporal stabilization provide the final guardrails.
        confidence = 0.75 if text else 0.0
        return FieldReading(text or None, confidence, text)

