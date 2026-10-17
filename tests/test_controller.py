from __future__ import annotations

import numpy as np

from rox_overlay.capture.base import WindowInfo
from rox_overlay.controller import RecognitionController
from rox_overlay.domain import ItemType
from rox_overlay.recognition.models import Rect
from rox_overlay.recognition.stability import RecognizedState


WINDOW = WindowInfo(4, "Ragnarok X", Rect(0, 0, 1280, 720))
READING = RecognizedState(ItemType.ARMOR, 14, 0.5, 0.9, Rect(900, 40, 370, 650))


class FakeCapture:
    def __init__(self) -> None:
        self.available = True
        self.calls = 0

    def capture(self, window: WindowInfo) -> np.ndarray | None:
        self.calls += 1
        return np.zeros((10, 10, 3), dtype=np.uint8) if self.available else None


class FakePipeline:
    def __init__(self) -> None:
        self.reading: RecognizedState | None = READING

    def recognize(self, frame: np.ndarray) -> RecognizedState | None:
        return self.reading


def make_controller(discovery=None) -> tuple[RecognitionController, FakeCapture, FakePipeline]:
    capture = FakeCapture()
    pipeline = FakePipeline()
    controller = RecognitionController(capture, pipeline, unit_price=100, discovery=discovery)
    return controller, capture, pipeline


def test_controller_targets_five_frames_per_second() -> None:
    controller, _, _ = make_controller()
    assert controller.interval_ms == 200


def test_publishes_after_three_frames_and_uses_live_price() -> None:
    controller, _, _ = make_controller()
    snapshots = []
    controller.snapshot_ready.connect(snapshots.append)
    controller.set_window(WINDOW)

    controller.tick_once()
    controller.tick_once()
    assert snapshots == []
    controller.tick_once()
    assert snapshots[-1].estimate.remaining_zeny == 57_000 * 100

    controller.set_unit_price(7)
    controller.tick_once()
    assert snapshots[-1].estimate.remaining_zeny == 57_000 * 7


def test_hides_after_five_invalid_frames_and_recovers_after_three() -> None:
    controller, _, pipeline = make_controller()
    hidden = []
    snapshots = []
    controller.overlay_hidden.connect(lambda: hidden.append(True))
    controller.snapshot_ready.connect(snapshots.append)
    controller.set_window(WINDOW)
    for _ in range(3):
        controller.tick_once()

    pipeline.reading = None
    for _ in range(5):
        controller.tick_once()
    assert hidden == [True]

    pipeline.reading = READING
    count = len(snapshots)
    for _ in range(3):
        controller.tick_once()
    assert len(snapshots) == count + 1


def test_unavailable_window_reports_status_without_spinning() -> None:
    controller, capture, _ = make_controller()
    statuses = []
    controller.status_changed.connect(statuses.append)
    controller.set_window(WINDOW)
    capture.available = False

    controller.tick_once()

    assert capture.calls == 1
    assert statuses[-1] == "janela_indisponivel"


def test_translates_detected_panel_to_screen_coordinates() -> None:
    controller, _, _ = make_controller()
    snapshots = []
    controller.snapshot_ready.connect(snapshots.append)
    controller.set_window(WindowInfo(4, "Ragnarok X", Rect(100, 50, 1280, 720)))

    for _ in range(3):
        controller.tick_once()

    assert snapshots[-1].panel_rect == Rect(1000, 90, 370, 650)


def test_reacquires_window_geometry_while_monitoring() -> None:
    class MovingDiscovery:
        def list_windows(self):
            return []

        def reacquire(self, previous: WindowInfo) -> WindowInfo | None:
            return WindowInfo(previous.handle, previous.title, Rect(200, 75, 1280, 720))

    controller, _, _ = make_controller(MovingDiscovery())
    snapshots = []
    controller.snapshot_ready.connect(snapshots.append)
    controller.set_window(WINDOW)

    for _ in range(3):
        controller.tick_once()

    assert snapshots[-1].panel_rect == Rect(1100, 115, 370, 650)


def test_does_not_emit_duplicate_stable_snapshots() -> None:
    controller, _, _ = make_controller()
    snapshots = []
    controller.snapshot_ready.connect(snapshots.append)
    controller.set_window(WINDOW)

    for _ in range(6):
        controller.tick_once()

    assert len(snapshots) == 1


def test_pause_hides_published_overlay_and_resume_restabilizes() -> None:
    controller, _, _ = make_controller()
    hidden = []
    snapshots = []
    controller.overlay_hidden.connect(lambda: hidden.append(True))
    controller.snapshot_ready.connect(snapshots.append)
    controller.set_window(WINDOW)
    for _ in range(3):
        controller.tick_once()

    controller.pause()
    assert hidden == [True]
    controller.resume()
    count = len(snapshots)
    for _ in range(2):
        controller.tick_once()
    assert len(snapshots) == count
    controller.tick_once()
    assert len(snapshots) == count + 1


def test_converts_physical_panel_pixels_to_qt_coordinates_at_high_dpi() -> None:
    controller, _, _ = make_controller()
    snapshots = []
    controller.snapshot_ready.connect(snapshots.append)
    window = WindowInfo(
        4,
        "Ragnarok X",
        Rect(1920, 0, 1920, 1080),
        dpi_scale=1.5,
        monitor_x=1920,
        monitor_y=0,
    )
    controller.set_window(window)

    for _ in range(3):
        controller.tick_once()

    assert snapshots[-1].panel_rect == Rect(2520, 27, 247, 433)
