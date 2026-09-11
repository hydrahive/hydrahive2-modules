"""Frontend-Vertrag des Musicplayer-Moduls für den Buddy-Media-Slot."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_musicplayer_registers_a_stable_buddy_media_widget():
    source = (ROOT / "frontend/index.tsx").read_text()

    assert "buddyMediaWidgets" in source
    assert 'id: "musicplayer"' in source
    assert "component: MusicPlayerBuddyBox" in source
