"""Gleichzeitige Aufträge dürfen sich die Szenen-Datei nicht gegenseitig überschreiben (gefunden 18.10.: zwei Videos in
derselben Szene → `…json.tmp` fehlte beim Umbenennen, und eine Shot-Änderung konnte verloren gehen)."""
from __future__ import annotations

import threading

from _gen_helpers import P
from conftest import PROJECT_ID


def _hammer(n_threads: int, fn) -> list[BaseException]:
    errors: list[BaseException] = []
    start = threading.Barrier(n_threads)

    def run(i: int) -> None:
        try:
            start.wait()
            fn(i)
        except BaseException as e:                     # noqa: BLE001 - jeder Fehler zählt
            errors.append(e)
    threads = [threading.Thread(target=run, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(20)
    return errors


def test_write_json_same_file_from_many_threads(ws) -> None:
    from backend._store import read_json, write_json
    path = ws / "studio" / "x.json"

    def write(i: int) -> None:
        for k in range(40):
            write_json(path, {"thread": i, "k": k})
    assert _hammer(8, write) == []
    assert isinstance(read_json(path, None), dict)
    assert not list(path.parent.glob("*.tmp*"))                                        # keine Reste


def test_parallel_shot_updates_keep_every_change(client, auth_headers, ws) -> None:
    from backend import generate_video
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Hafen"}).json()
    ids = [client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": f"p{i}"}).json()["id"] for i in range(6)]

    def update(i: int) -> None:
        for k in range(15):
            generate_video._set_shot(PROJECT_ID, sc["id"], ids[i], prompt=f"thread{i}-{k}")
    assert _hammer(6, update) == []
    shots = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"]
    assert [s["prompt"] for s in shots] == [f"thread{i}-14" for i in range(6)]          # keine Änderung verloren


def test_parallel_attach_keeps_every_image(client, auth_headers, ws) -> None:
    """Zwei Bilder für verschiedene Shots derselben Szene gleichzeitig fertig → beide hängen am richtigen Shot."""
    from _gen_helpers import PNG

    from backend import generate
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Hafen"}).json()
    ids = [client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": f"p{i}"}).json()["id"] for i in range(8)]
    d = ws / "studio/media/images"
    d.mkdir(parents=True, exist_ok=True)
    for i in range(8):
        for k in range(8):
            (d / f"{i}-{k}.png").write_bytes(PNG)

    def attach(i: int) -> None:
        for k in range(8):                              # jedes Bild einmal → am Ende 8 Varianten je Shot
            generate._attach(PROJECT_ID, sc["id"], ids[i], f"studio/media/images/{i}-{k}.png")
    assert _hammer(8, attach) == []
    shots = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"]
    assert [s["image_rel"] for s in shots] == [f"studio/media/images/{i}-7.png" for i in range(8)]
    assert [len(s["variants"]) for s in shots] == [8] * 8                               # keine Variante verloren
