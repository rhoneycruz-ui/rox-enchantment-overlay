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



@dataclass
class RichBackend(FakeBackend):
    foreground: int = 0
    pids: dict[int, int] | None = None
    cursor: tuple[int, int] | None = None
    alive: set[int] | None = None
    enumerations: int = 0

    def handles(self) -> list[int]:
        self.enumerations += 1
        return super().handles()

    def is_window(self, handle: int) -> bool:
        return handle in (self.alive if self.alive is not None else set(self.handles()))

    def foreground_handle(self) -> int:
        return self.foreground

    def process_id(self, handle: int) -> int:
        return (self.pids or {}).get(handle, 1)

    def cursor_position(self) -> tuple[int, int] | None:
        return self.cursor


def test_reacquire_same_handle_does_not_enumerate_all_windows() -> None:
    rect = Rect(0, 0, 800, 600)
    backend = RichBackend([(7, "Game", True, rect)], alive={7})

    assert Win32WindowDiscovery(backend).reacquire(WindowInfo(7, "Game", rect)) is not None
    assert backend.enumerations == 0


def test_foreground_accepts_game_or_own_windows_only() -> None:
    import os

    rect = Rect(0, 0, 800, 600)
    backend = RichBackend([(7, "Game", True, rect)], pids={50: os.getpid()})
    discovery = Win32WindowDiscovery(backend)
    game = WindowInfo(7, "Game", rect)

    backend.foreground = 7
    assert discovery.is_foreground(game)
    backend.foreground = 50
    assert discovery.is_foreground(game)
    backend.foreground = 99
    assert not discovery.is_foreground(game)


def test_lists_skip_own_windows_and_count_duplicate_titles() -> None:
    import os

    rect = Rect(0, 0, 800, 600)
    backend = RichBackend(
        [(7, "Game", True, rect), (8, " game ", True, rect), (9, "Overlay", True, rect)],
        pids={9: os.getpid()},
    )
    discovery = Win32WindowDiscovery(backend)

    assert [window.handle for window in discovery.list_windows()] == [7, 8]
    assert discovery.title_count("GAME") == 2


def test_cursor_inside_uses_client_rect() -> None:
    backend = RichBackend([(7, "Game", True, Rect(100, 100, 50, 50))])
    discovery = Win32WindowDiscovery(backend)
    game = WindowInfo(7, "Game", Rect(100, 100, 50, 50))

    backend.cursor = (120, 149)
    assert discovery.cursor_inside(game)
    backend.cursor = (150, 120)
    assert not discovery.cursor_inside(game)
