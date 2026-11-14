"""Rebuild assets/stones/*.png from the screenshots in tests/fixtures.

Run after adding a screenshot of a new stone (e.g. after a game patch):
    python scripts/make_stone_templates.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rox_overlay.domain import ItemType  # noqa: E402
from rox_overlay.recognition.panel import REFERENCE_PANEL_WIDTH, PanelDetector  # noqa: E402
from rox_overlay.recognition.stones import city_slug, default_template_dir, template_from_icon  # noqa: E402

logger = logging.getLogger("make_stone_templates")
FIXTURES = ROOT / "tests" / "fixtures"


def sources() -> dict[str, Path]:
    """template name (city-item) -> screenshot it is cut from."""
    found = {
        f"{city_slug('Prontera')}-{item.value}": FIXTURES / "panels" / f"{item.value}-panel.png" for item in ItemType
    }
    found.update({f"payon-{item.value}": FIXTURES / "screens" / f"{item.value}-15.png" for item in ItemType})
    found.update({path.stem: path for path in sorted((FIXTURES / "stones").glob("*.png"))})
    return found


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    out = default_template_dir()
    out.mkdir(parents=True, exist_ok=True)
    detector = PanelDetector()
    failures = 0
    for name, path in sources().items():
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        detection = detector.detect(frame) if frame is not None else None
        if detection is None:
            logger.error("painel não encontrado em %s", path)
            failures += 1
            continue
        width = detection.rect.width
        if abs(width - REFERENCE_PANEL_WIDTH) > REFERENCE_PANEL_WIDTH * 0.05:
            logger.error("%s: painel com %d px de largura (esperado ~%d)", path, width, REFERENCE_PANEL_WIDTH)
            failures += 1
            continue
        icon = detector.extract_regions(frame, detection).cost_icon
        assert icon is not None
        if width != REFERENCE_PANEL_WIDTH:
            factor = REFERENCE_PANEL_WIDTH / width
            icon = cv2.resize(icon, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / f"{name}.png"), template_from_icon(icon))
        logger.info("%s <- %s", name, path.name)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
