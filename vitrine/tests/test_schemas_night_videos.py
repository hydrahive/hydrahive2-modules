from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas import Config

EMPTY_POOLS = {"spring": [], "summer": [], "autumn": [], "winter": []}


def test_nachtvideo_defaults_enthalten_vier_saison_pools():
    night = Config().dump()["night"]
    assert night == {
        "enabled": False,
        "from": "23:00",
        "to": "07:00",
        "mode": "dim",
        "videos": EMPTY_POOLS,
    }


def test_nachtvideo_modus_und_pools_werden_gespeichert():
    pools = {**EMPTY_POOLS, "spring": ["hydra-schlaf-fruehling-01.mp4"]}
    night = Config(night={
        "enabled": True,
        "from": "22:30",
        "to": "06:30",
        "mode": "video",
        "videos": pools,
    }).dump()["night"]

    assert night["mode"] == "video"
    assert night["videos"] == pools


@pytest.mark.parametrize("videos", [
    {**EMPTY_POOLS, "monsoon": ["regen.mp4"]},
    {**EMPTY_POOLS, "winter": ["../ausbruch.mp4"]},
    {**EMPTY_POOLS, "winter": ["kein-video.txt"]},
    {**EMPTY_POOLS, "winter": "film.mp4"},
])
def test_nachtvideo_pools_weisen_unbekannte_saison_und_namen_ab(videos):
    with pytest.raises(ValidationError):
        Config(night={"mode": "video", "videos": videos})
