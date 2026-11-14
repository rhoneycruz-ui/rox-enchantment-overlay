from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_windows_ci_runs_supported_python_and_full_suite() -> None:
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

    assert "windows-latest" in workflow
    assert '"3.12"' in workflow and '"3.13"' in workflow
    assert "ruff check" in workflow
    assert "mypy" in workflow
    assert "QT_QPA_PLATFORM: offscreen" in workflow
    assert 'pip install -e ".[dev]"' in workflow
    assert "python -m pytest" in workflow


def test_readme_leads_with_verified_download_and_visuals() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "actions/workflows/tests.yml/badge.svg" in readme
    assert "releases/latest/download/ROX-Enchantment-Overlay-portable.zip" in readme
    assert "docs/assets/rox-overlay-banner.png" in readme
    assert "docs/assets/settings-window.png" in readme


def test_readme_visual_assets_are_real_png_files() -> None:
    for relative_path in (
        "docs/assets/rox-overlay-banner.png",
        "docs/assets/settings-window.png",
    ):
        image = ROOT / relative_path
        assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_release_workflow_publishes_zip_with_checksum() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "ROX-Enchantment-Overlay-portable.zip.sha256" in workflow
    assert "--self-test" in workflow
