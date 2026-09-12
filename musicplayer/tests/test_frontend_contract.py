"""Frontend-Vertrag des Musicplayer-Moduls für den Buddy-Media-Slot."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_musicplayer_registers_a_stable_buddy_media_widget():
    source = (ROOT / "frontend/index.tsx").read_text()

    assert "buddyMediaWidgets" in source
    assert 'id: "musicplayer"' in source
    assert "component: MusicPlayerBuddyBox" in source


def test_buddy_player_uses_the_new_cockpit_panel_contract():
    player = (ROOT / "frontend/MusicPlayerBuddyBox.tsx").read_text()
    panel = (ROOT / "frontend/MusicPlayerPanel.tsx").read_text()

    assert "CollapsibleBox" not in player
    assert "w-60" not in player
    assert "w-full" in panel
    assert 'rounded-[4px]' in panel
    assert "#151c2b" in panel
    assert "#2a364b" in panel
    assert "hh2.box.buddy-musicplayer" in panel
    assert "MEDIA" in panel


def test_admin_player_actions_use_cockpit_surfaces():
    upload = (ROOT / "frontend/UploadButton.tsx").read_text()
    generated = (ROOT / "frontend/GeneratedImport.tsx").read_text()

    for source in (upload, generated):
        assert 'rounded-[4px]' in source
        assert "#2a364b" in source
        assert "rounded-lg" not in source


def test_player_is_keyed_to_the_active_project_and_has_no_global_fallback():
    buddy = (ROOT / "frontend/MusicPlayerBuddyBox.tsx").read_text()

    assert "projectId" in buddy
    assert "if (!projectId)" in buddy
    assert "mp_select_project" in buddy
    assert "<MusicPlayerProjectView key={projectId} projectId={projectId}" in buddy


def test_frontend_api_is_project_scoped_and_downloads_with_auth_header():
    api = (ROOT / "frontend/api.ts").read_text()

    assert "projectId" in api
    assert "encodeURIComponent(projectId)" in api
    assert "download: async" in api
    assert "Authorization" in api
    assert "download=1" in api


def test_project_view_uses_effective_permissions_and_offers_download():
    view = (ROOT / "frontend/MusicPlayerProjectView.tsx").read_text()

    assert "permissions.can_upload" in view
    assert "permissions.can_delete" in view
    assert "musicApi.download(projectId, track)" in view
    assert "mp_download" in view
