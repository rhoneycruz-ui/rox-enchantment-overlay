# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)

1. **[2026-10-16] Reject Poppler's `icuuc.dll` from PyInstaller Qt bundles**
   Do instead: filter the `icuuc.dll` whose source path contains `poppler` from `Analysis.binaries`; otherwise it shadows Windows ICU and PySide6.QtCore fails with WinError 127. Validate by checking the final archive has no root `_internal/icuuc.dll` and that the packaged settings window—not merely the process—opens.

## Shell & Command Reliability

## Domain Behavior Guardrails

1. **[2026-10-16] Prontera has equal Muspellium cost per enchant point**
   Do instead: calculate weapon as 90 Muspellium/3 points and armor/accessory as 30 Muspellium/1 point; all equal 30 Muspellium per point.
2. **[2026-10-16] Use the scraped level-point curve as authoritative local data**
   Do instead: use 1→2 through 19→20 points: 10, 30, 60, 100, 150, 250, 400, 600, 850, 1150, 1550, 2050, 2800, 3800, 5050, 6550, 8300, 10300, 12550.
3. **[2026-10-16] Classify enchantment type from the title under the item**
   Do instead: OCR normalized Portuguese/English keywords arma/weapon, armadura/armor/armour, and acessorio/accessory; never rely primarily on equipment artwork.

## User Directives

1. **[2026-10-16] Use the compact overlay anchored left of the enchantment panel**
   Do instead: keep it click-through, auto-hide it with the panel, and expose 25–100% background opacity in settings.

