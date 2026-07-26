from __future__ import annotations

from pathlib import Path

FRONTEND = Path(__file__).parents[1] / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_canonical_frontend_is_a_cockpit_module() -> None:
    index = _read("index.tsx")
    assert 'path: "/mediacenter"' in index
    assert "cockpit: true" in index
    assert "Radarr" not in index
    assert "Sonarr" not in index


def test_frontend_api_uses_only_the_v1_mediacenter_routes() -> None:
    source = _read("api.ts")
    for route in (
        '`${BASE}/status`',
        '`${BASE}/connections/test`',
        '`${BASE}/search`',
        '`${BASE}/enqueue`',
        '`${BASE}/queue`',
        '`${BASE}/history`',
    ):
        assert route in source
    assert "http://" not in source
    assert "https://" not in source


def test_frontend_renders_all_v1_views_without_destructive_actions() -> None:
    page = _read("MediacenterPage.tsx")
    assert "ConnectionStatus" in page
    assert "SearchPanel" in page
    assert "ResultList" in page
    assert "JobsPanel" in page
    combined = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.glob("*.tsx"))
    assert "mediacenterApi.enqueue" in combined
    assert "mediacenterApi.queue" in combined
    assert "mediacenterApi.history" in combined
    assert "mediacenterApi.cancel" not in combined
    assert "mediacenterApi.delete" not in combined
