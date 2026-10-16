# ROX Enchantment Cost Overlay — Design Specification

Date: 2026-10-16
Status: Approved

## 1. Purpose

Build a Windows desktop assistant for Ragnarok X that detects the open enchantment panel, determines whether the selected item is a weapon, armor, or accessory, reads the current enchantment level and progress bar, and displays the remaining Muspellium and Zeny cost in a compact overlay.

The application is a read-only visual assistant. It does not click, inject code, read game memory, or modify the game process.

## 2. Success Criteria

- Detect the enchantment panel while it is visible in the selected game window.
- Work at different game resolutions and window positions.
- Recognize weapon, armor, and accessory panels in Portuguese and English.
- Read enchantment levels 1 through 19 and calculate the requirement for the next level, up to level 20.
- Estimate the progress bar reliably despite glow and animation.
- Show remaining points, Muspellium, and Zeny in a click-through overlay anchored to the left of the enchantment panel.
- Allow the user to configure Muspellium price and overlay opacity.
- Run locally without sending screenshots or game information to an external service.
- Be distributable to other Windows users without requiring a Python installation.

## 3. Out of Scope

- Clicking the Refine button or automating any game input.
- Reading or modifying game memory.
- Injecting code into the game process.
- Calculating enchantment costs for cities other than Prontera.
- Supporting levels above 20.
- Fetching live market prices automatically.

## 4. Authoritative Level Data

The following values were extracted directly from the referenced Methax enchanting calculator on 2026-10-16.

| Current level | Next level | Required points |
|---:|---:|---:|
| 1 | 2 | 10 |
| 2 | 3 | 30 |
| 3 | 4 | 60 |
| 4 | 5 | 100 |
| 5 | 6 | 150 |
| 6 | 7 | 250 |
| 7 | 8 | 400 |
| 8 | 9 | 600 |
| 9 | 10 | 850 |
| 10 | 11 | 1,150 |
| 11 | 12 | 1,550 |
| 12 | 13 | 2,050 |
| 13 | 14 | 2,800 |
| 14 | 15 | 3,800 |
| 15 | 16 | 5,050 |
| 16 | 17 | 6,550 |
| 17 | 18 | 8,300 |
| 18 | 19 | 10,300 |
| 19 | 20 | 12,550 |

Prontera enchantment rules:

| Item type | Muspellium per tap | Points per tap | Muspellium per point |
|---|---:|---:|---:|
| Weapon | 90 | 3 | 30 |
| Armor | 30 | 1 | 30 |
| Accessory | 30 | 1 | 30 |

## 5. User Experience

### 5.1 First Run

1. The application starts in the system tray and opens a small settings window.
2. It attempts to find a likely Ragnarok X window.
3. If automatic discovery fails or finds multiple candidates, the user chooses the game window from a list.
4. The user enters the current price of one Muspellium and chooses overlay opacity.
5. The application stores these settings locally.

### 5.2 Normal Use

1. The assistant captures only the selected game window at a target rate of 5 frames per second.
2. When no enchantment panel is detected, the overlay remains hidden and the tray status reads `Aguardando painel`.
3. When the panel is detected reliably, the assistant reads its state and shows the overlay.
4. The overlay follows the panel if the game window moves or changes size.
5. The overlay disappears when the panel closes or recognition confidence drops below the safe threshold.

### 5.3 Overlay

The approved compact overlay contains:

- Detected item type and level transition, such as `Armadura · 14 → 15`.
- A live-status indicator.
- Remaining enchantment points.
- Estimated progress bar.
- Remaining Muspellium.
- Remaining Zeny cost.

The overlay is:

- Anchored 12 pixels to the left of the detected enchantment panel.
- Clamped inside the active monitor's usable area.
- Moved to the nearest non-overlapping safe position if there is insufficient space on the left.
- Always on top of the game window while the panel is open.
- Click-through, so it never blocks game interaction.
- Hidden from the capture source where supported, preventing the assistant from recognizing its own overlay.

### 5.4 Settings

The tray menu opens a separate settings window containing:

- Selected game window.
- `Detectar novamente` action.
- Muspellium unit price in Zeny.
- Overlay background opacity from 25% to 100%, defaulting to 82%.
- Optional horizontal and vertical position offsets.
- Pause/resume recognition.
- Exit application.

Opacity affects only the overlay background. Text and values remain fully opaque for readability.

## 6. Recognition Pipeline

### 6.1 Window Capture

- Capture only the client area of the selected window.
- Prefer a Windows GPU-backed capture method.
- Fall back to a conventional desktop-region capture method if the primary backend is unavailable.
- Do not require the game window to be focused, provided the capture backend can still access it.
- Exclusive fullscreen support is best-effort; borderless or windowed modes are the supported baseline.

### 6.2 Panel Detection

The detector locates the enchantment panel using multiple stable anchors rather than fixed screen coordinates:

- Outer panel shape and proportions.
- Central circular enchantment graphic.
- Level/progress-bar region.
- Refine/cost region near the bottom.

Detection runs across a bounded range of image scales. Once found, every recognition region is expressed as normalized coordinates relative to the panel rectangle. This makes the pipeline independent of absolute resolution and position.

### 6.3 Item-Type Recognition

The primary signal is the title directly below the item image. OCR output is lowercased, stripped of accents, and normalized before keyword matching.

| Type | Portuguese tokens | English tokens |
|---|---|---|
| Weapon | `arma` | `weapon` |
| Armor | `armadura` | `armor`, `armour` |
| Accessory | `acessorio` | `accessory` |

The recognizer matches distinctive keywords rather than requiring an exact phrase or word order. It therefore accepts labels such as `Nível da Arma`, `Weapon Level`, or equivalent ordering.

The equipment artwork is not used as the primary classifier because its appearance changes with the selected item.

### 6.4 Level Recognition

- Crop the large numeric level field to the left of the progress bar.
- Upscale and normalize contrast before OCR.
- Restrict accepted output to integers from 1 through 20.
- Require agreement across at least three recent valid frames before changing the displayed level.
- Level 20 is displayed as maximum level and produces no remaining-cost calculation.

### 6.5 Progress Recognition

- Detect the progress track endpoints from the normalized panel region.
- Segment the cyan filled portion using color and luminance, not a single hard-coded RGB value.
- Reduce animation noise by taking the median of seven recent valid measurements.
- Clamp the normalized result to the range 0 through 1.
- Reject a frame when track endpoints or fill boundaries cannot be found confidently.

## 7. Calculation Rules

Definitions:

- `R`: total required points for the current level.
- `p`: measured progress fraction from 0 through 1.
- `q`: points per tap; 3 for weapon and 1 for armor/accessory.
- `m`: Muspellium per tap; 90 for weapon and 30 for armor/accessory.
- `u`: user-entered Zeny price per Muspellium.

Calculations:

1. `estimated_earned = R × p`
2. `earned = clamp(round(estimated_earned ÷ q) × q, 0, R)`
3. `remaining_points = max(0, R - earned)`
4. `remaining_taps = ceil(remaining_points ÷ q)`
5. `remaining_muspellium = remaining_taps × m`
6. `remaining_zeny = remaining_muspellium × u`

Snapping earned points to a reachable tap increment reduces small visual errors from the animated bar. The overlay labels the result as an estimate because the game does not show an exact numeric progress value.

## 8. Stability and Failure Handling

Each candidate reading receives confidence scores for panel detection, item type, level, and bar progress.

- Show the overlay only after three consecutive compatible readings.
- Update values only when the stabilized reading changes.
- Keep the last valid reading for up to five failed frames to avoid flicker.
- Hide the overlay after five consecutive invalid or incompatible frames.
- Never show a calculation when item type or level is unknown.
- Show diagnostic status only in the settings window, not over the game.
- Log compact local diagnostics without retaining screenshots by default.
- Provide an explicit troubleshooting option to save one annotated screenshot when the user chooses to do so.

## 9. Components

### Window Discovery

Enumerates visible top-level windows, remembers the chosen window identity, and reacquires it after a game restart when possible.

### Capture Service

Produces frames from the selected window and exposes capture health without knowing anything about enchanting.

### Panel Detector

Returns a panel rectangle and confidence score from a frame.

### State Recognizer

Consumes the normalized panel image and returns item type, current level, progress fraction, and per-field confidence.

### Stabilizer

Combines recent recognition results and publishes only a stable state.

### Cost Calculator

Contains the immutable level table and pure calculation functions. It has no image or UI dependencies.

### Overlay Window

Renders the approved compact layout and positions it relative to the detected panel.

### Settings and Persistence

Owns price, opacity, offsets, selected-window preference, and application state. Settings are stored in a local user configuration file.

## 10. Technology Direction

- Python 3.12 application.
- PySide6 for the settings and transparent overlay windows.
- OpenCV for panel detection and progress segmentation.
- Offline OCR with Portuguese and English support for the small title and level regions.
- A Windows capture backend with a conventional screen-capture fallback.
- A Windows self-contained distribution built without requiring Python on the recipient's machine.

The implementation plan must validate the capture and OCR packages against current Windows and packaging support before locking their exact adapters.

## 11. Performance Targets

- Recognition target: 5 frames per second during active monitoring.
- UI remains responsive while capture and recognition run on worker threads.
- Overlay updates are rate-limited to prevent visible jitter.
- Heavy recognition is limited to the game window and then to panel-relative crops.
- When the game window is minimized or unavailable, active recognition pauses.

## 12. Validation Plan

### Unit Tests

- All 19 level transitions return the correct required points.
- Weapon calculations round to three-point taps and 90 Muspellium units.
- Armor and accessory calculations use one-point taps and 30 Muspellium units.
- Zero, partial, and full progress cases.
- Price values including zero and large integers.
- Level 20 maximum-level behavior.

### Recognition Fixtures

Maintain approved screenshots covering:

- Weapon, armor, and accessory.
- Portuguese and English titles.
- Levels 1 through 20, prioritizing visually confusable two-digit levels.
- Empty, partial, and nearly full progress bars.
- Multiple resolutions, Windows DPI scales, brightness levels, and panel positions.

Expected panel rectangle, type, level, and progress range are stored with each fixture.

### Integration Tests

- Start with no game window.
- Select and reacquire the game window.
- Open and close the enchantment panel.
- Move and resize the game window.
- Change opacity and Muspellium price while recognition is active.
- Confirm the overlay does not intercept mouse input.
- Confirm invalid readings hide values rather than displaying stale calculations indefinitely.

### Packaging Test

Test the packaged application on a clean Windows 10/11 environment without Python installed.

## 13. Distribution

The initial release is a portable ZIP containing the executable and required runtime files. This is preferred over a single compressed executable because it has faster startup and fewer antivirus false positives. A signed installer can be considered later if distribution grows.

The package includes:

- Application executable and runtime files.
- Portuguese and English OCR resources.
- Default recognition templates.
- A concise usage and troubleshooting guide.

## 14. Privacy and Game Safety

- Screenshots are processed in memory and discarded.
- No image, OCR result, window title, or usage data is transmitted.
- No game input automation is implemented.
- No process injection, memory inspection, or network interception is implemented.
- Users remain responsible for checking the game's current rules regarding third-party overlays.

