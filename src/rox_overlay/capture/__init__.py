"""Game-window discovery and frame capture backends."""

from .base import FrameSource, WindowDiscovery, WindowInfo
from .fallback import CascadingFrameSource, MssCaptureSource
from .windows import Win32WindowDiscovery, WindowsCaptureSource

__all__ = [
    "CascadingFrameSource",
    "FrameSource",
    "MssCaptureSource",
    "Win32WindowDiscovery",
    "WindowDiscovery",
    "WindowInfo",
    "WindowsCaptureSource",
]
