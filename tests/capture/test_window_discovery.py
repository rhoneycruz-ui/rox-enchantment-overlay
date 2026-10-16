from __future__ import annotations

from dataclasses import dataclass

from rox_overlay.capture.base import WindowInfo
from rox_overlay.capture.windows import Win32WindowDiscovery, normalize_window_title
from rox_overlay.recognition.models import Rect


@dataclass
class FakeBackend:
    entries: list[tuple[int, str, bool, Rect]]

    def handles(self) -> list[int]:
        return [entry[0] for entry in self.entries]

    def is_visible(self, handle: int) -> bool:
        return next(entry[2] for entry in self.entries if entry[0] == handle)

    def title(self, handle: int) -> str:
        return next(entry[1] for entry in self.entries if entry[0] == handle)

    def client_rect(self, handle: int) -> Rect | None:
        return next(entry[3] for entry in self.entries if entry[0] == handle)


def test_lists_only_visible_titled_windows() -> None:
    backend = FakeBackend([
        (1, "Ragnarok X", True, Rect(10, 20, 1280, 720)),
        (2, "Hidden", False, Rect(0, 0, 100, 100)),
        (3, "", True, Rect(0, 0, 100, 100)),
    ])

    assert Win32WindowDiscovery(backend).list_windows() == [
        WindowInfo(1, "Ragnarok X", Rect(10, 20, 1280, 720))
    ]


def test_reacquires_changed_handle_using_normalized_title() -> None:
    backend = FakeBackend([(9, "  RAGNAROK   X  ", True, Rect(30, 40, 1280, 720))])
    previous = WindowInfo(1, "Ragnarok X", Rect(10, 20, 1280, 720))

    reacquired = Win32WindowDiscovery(backend).reacquire(previous)

    assert reacquired is not None
    assert reacquired.handle == 9
    assert normalize_window_title(reacquired.title) == "ragnarok x"


def test_reacquire_prefers_same_handle_among_multiple_candidates() -> None:
    rect = Rect(0, 0, 800, 600)
    backend = FakeBackend([(8, "Game", True, rect), (7, "Game", True, rect)])

    assert Win32WindowDiscovery(backend).reacquire(WindowInfo(7, "Game", rect)).handle == 7

