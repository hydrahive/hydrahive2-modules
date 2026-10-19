"""Studio 7c: Warteschlange für die Ausgabe (studio/SPEC.md „7c im Detail“)."""
from __future__ import annotations

import threading
import time

import pytest
from _render_helpers import R, clip, needs_ffmpeg, put_timeline
from conftest import PROJECT_ID


def _image_timeline(client, h, ws, n: int = 1) -> None:
    b = ws / "studio/media/images"
    b.mkdir(parents=True, exist_ok=True)
    (b / "x.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    put_timeline(client, h, [clip("image", i * 2, 0, 2, "studio/media/images/x.png") for i in range(n)])


def _jobs(client, h) -> list[dict]:
    return [j for j in client.get(f"{R}/plan/jobs", headers=h).json()["jobs"] if j["kind"] == "render"]


def _until(fn, timeout: float = 10.0):
    end = time.time() + timeout
    while time.time() < end:
        got = fn()
        if got:
            return got
        time.sleep(0.05)
    raise AssertionError("Zustand nicht erreicht")


class FakeFfmpeg:
    """Ersetzt _run_ffmpeg: merkt sich die Reihenfolge (Ausgabegröße) und wartet, bis der Test den Film freigibt."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.gates: list[threading.Event] = []
        self.lock = threading.Lock()
        self.open = False                                   # nach dem Test: nichts mehr aufhalten

    def __call__(self, cmd, seconds, progress):
        graph = cmd[cmd.index("-filter_complex") + 1]
        size = graph.split("scale=", 1)[1].split(":force", 1)[0]
        gate = threading.Event()
        if self.open:
            gate.set()
        with self.lock:
            self.calls.append(size)
            self.gates.append(gate)
        while not gate.wait(0.05):
            progress(0.4)                                   # Fortschritt melden – hier greift auch das Abbrechen
        open(cmd[-1], "wb").close()

    def release(self, i: int) -> None:
        _until(lambda: len(self.gates) > i)
        self.gates[i].set()


@pytest.fixture
def fake(monkeypatch):
    from backend import render
    f = FakeFfmpeg()
    monkeypatch.setattr(render, "_run_ffmpeg", f)
    yield f
    f.open = True
    for g in f.gates:
        g.set()


def test_clicks_queue_up_in_order_one_at_a_time(client, auth_headers, ws, fake) -> None:
    _image_timeline(client, auth_headers, ws)
    bodies = [{"aspect": "16:9", "quality": "preview"}, {"aspect": "9:16", "quality": "preview"}, {"aspect": "1:1", "quality": "preview"}]
    started = [client.post(f"{R}/render", headers=auth_headers, json=b) for b in bodies]
    assert [r.status_code for r in started] == [202, 202, 202]
    assert [r.json()["position"] for r in started] == [1, 2, 3]
    _until(lambda: fake.calls)
    time.sleep(0.3)
    assert fake.calls == ["854:480"]                                                   # nur einer läuft
    states = {j["id"]: j["status"] for j in _jobs(client, auth_headers)}
    assert [states[r.json()["id"]] for r in started] == ["running", "queued", "queued"]
    info = {j["id"]: j["info"] for j in _jobs(client, auth_headers)}[started[1].json()["id"]]
    assert info == {"aspect": "9:16", "quality": "preview", "subtitles": False}
    for i in range(3):
        fake.release(i)
    _until(lambda: all(j["status"] == "done" for j in _jobs(client, auth_headers)) and len(_jobs(client, auth_headers)) == 3)
    assert fake.calls == ["854:480", "480:854", "480:480"]                             # Reihenfolge der Klicks
    assert len(client.get(f"{R}/renders", headers=auth_headers).json()["renders"]) == 3


def test_at_most_five_per_project(client, auth_headers, ws, fake) -> None:
    _image_timeline(client, auth_headers, ws)
    ok = [client.post(f"{R}/render", headers=auth_headers, json={}) for _ in range(5)]
    assert all(r.status_code == 202 for r in ok)
    r = client.post(f"{R}/render", headers=auth_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "studio_render_queue_full"
    assert len(_jobs(client, auth_headers)) == 5
    fake.release(0)                                                                    # einer fertig → Platz frei
    _until(lambda: any(j["status"] == "done" for j in _jobs(client, auth_headers)))
    assert client.post(f"{R}/render", headers=auth_headers, json={}).status_code == 202
    for i in range(1, 6):
        fake.release(i)


def test_cancel_waiting_film(client, auth_headers, ws, fake) -> None:
    _image_timeline(client, auth_headers, ws)
    first = client.post(f"{R}/render", headers=auth_headers, json={"quality": "preview"}).json()
    second = client.post(f"{R}/render", headers=auth_headers, json={"quality": "high"}).json()
    assert client.post(f"{R}/plan/jobs/{second['id']}/cancel", headers=auth_headers, json={}).status_code == 200
    _until(lambda: {j["id"]: j["status"] for j in _jobs(client, auth_headers)}[second["id"]] == "cancelled")
    fake.release(0)
    _until(lambda: {j["id"]: j["status"] for j in _jobs(client, auth_headers)}[first["id"]] == "done")
    time.sleep(0.3)
    assert fake.calls == ["854:480"]                                                   # der abgebrochene lief nie
    for _ in range(4):                                                                # sein Platz ist wieder frei
        assert client.post(f"{R}/render", headers=auth_headers, json={}).status_code == 202
    for i in range(1, 5):
        fake.release(i)


def test_cancel_running_film(client, auth_headers, ws, fake) -> None:
    _image_timeline(client, auth_headers, ws)
    first = client.post(f"{R}/render", headers=auth_headers, json={"quality": "preview"}).json()
    second = client.post(f"{R}/render", headers=auth_headers, json={"quality": "standard"}).json()
    _until(lambda: fake.calls)
    client.post(f"{R}/plan/jobs/{first['id']}/cancel", headers=auth_headers, json={})
    _until(lambda: {j["id"]: j["status"] for j in _jobs(client, auth_headers)}[first["id"]] == "cancelled")
    _until(lambda: len(fake.calls) == 2)                                              # der nächste startet
    assert fake.calls == ["854:480", "1280:720"]
    fake.release(1)
    _until(lambda: {j["id"]: j["status"] for j in _jobs(client, auth_headers)}[second["id"]] == "done")
    assert len(list((ws / "studio/renders").glob("*.mp4"))) == 1                       # keine halbe Datei
    assert not list((ws / "studio/renders").glob(".*part*"))


def test_finished_film_cannot_be_cancelled(client, auth_headers, ws, fake) -> None:
    _image_timeline(client, auth_headers, ws)
    job = client.post(f"{R}/render", headers=auth_headers, json={}).json()
    fake.release(0)
    _until(lambda: _jobs(client, auth_headers)[0]["status"] == "done")
    assert client.post(f"{R}/plan/jobs/{job['id']}/cancel", headers=auth_headers, json={}).json()["status"] == "done"
    time.sleep(0.2)
    assert _jobs(client, auth_headers)[0]["status"] == "done"


def test_queued_film_uses_the_edit_from_the_click(client, auth_headers, ws, fake) -> None:
    _image_timeline(client, auth_headers, ws, n=1)
    client.post(f"{R}/render", headers=auth_headers, json={})
    second = client.post(f"{R}/render", headers=auth_headers, json={}).json()
    _image_timeline(client, auth_headers, ws, n=3)                                    # danach weitergeschnitten
    fake.release(0)
    fake.release(1)
    done = _until(lambda: [j for j in _jobs(client, auth_headers) if j["id"] == second["id"] and j["status"] == "done"])
    assert done[0]["result"]["clips"] == 1 and done[0]["result"]["duration"] == 2


def test_queued_film_after_restart_is_interrupted(client, auth_headers, ws) -> None:
    import json
    (ws / "studio/jobs").mkdir(parents=True, exist_ok=True)
    (ws / f"studio/jobs/{'d' * 32}.json").write_text(json.dumps(
        {"id": "d" * 32, "kind": "render", "target": "render:" + "e" * 32, "scene_id": "", "status": "queued", "progress": {}}))
    got = {j["id"]: j for j in _jobs(client, auth_headers)}["d" * 32]
    assert got["status"] == "failed" and got["error"] == "interrupted"


def test_queue_is_shared_by_all_projects() -> None:
    """Ein Film zur Zeit auf dem ganzen Server, Reihenfolge der Anmeldung – auch über Projekte hinweg."""
    from backend import jobs, render_queue

    class P:
        def __init__(self, jid: str) -> None:
            self.job = {"id": jid, "status": "queued"}

        def set(self, **_) -> None:
            pass

        def cancelled(self) -> bool:
            return self.job["id"] in jobs._cancel

    order: list[str] = []
    tickets = [render_queue.enter(pid) for pid in ("p1", "p2", "p1")]
    assert [t[1] for t in tickets] == [1, 2, 3]
    gate = threading.Event()

    def run(ticket: str, name: str) -> None:
        with render_queue.turn(ticket, P(name)):
            order.append(name)
            gate.wait(5)
    threads = [threading.Thread(target=run, args=(t[0], n)) for t, n in zip(tickets, ("a", "b", "c"))]
    for t in reversed(threads):                                                        # Start-Reihenfolge egal
        t.start()
    time.sleep(0.3)
    assert order == ["a"]
    gate.set()
    for t in threads:
        t.join(5)
    assert order == ["a", "b", "c"]
    assert render_queue.pending("p1") == 0 and render_queue.pending("p2") == 0


def test_queue_limit_counts_only_own_project() -> None:
    from backend import render_queue
    mine = [render_queue.enter("q1")[0] for _ in range(render_queue.MAX_PER_PROJECT)]
    with pytest.raises(render_queue.QueueFull):
        render_queue.enter("q1")
    other = render_queue.enter("q2")[0]                                              # anderes Projekt: geht
    for t in [*mine, other]:
        render_queue.leave(t)
    assert render_queue.pending("q1") == 0


def test_cancel_while_waiting_leaves_the_line() -> None:
    from backend import jobs, render_queue
    first, _ = render_queue.enter("c1")
    second, _ = render_queue.enter("c1")

    class P:
        job = {"id": "x" * 32, "status": "queued"}

        def set(self, **_) -> None:
            pass

        def cancelled(self) -> bool:
            return True
    with pytest.raises(jobs.Cancelled), render_queue.turn(second, P()):
        pass
    assert render_queue.pending("c1") == 1
    render_queue.leave(first)


@needs_ffmpeg
def test_real_ffmpeg_is_stopped_on_cancel(tmp_path) -> None:
    """Wirft der Fortschritt (Abbrechen), wird ffmpeg beendet – nicht erst nach dem ganzen Film."""
    from backend import jobs, render
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin", "-re", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=25:d=60",
           "-c:v", "libx264", "-preset", "ultrafast", "-progress", "pipe:1", "-nostats", str(tmp_path / "o.mp4")]
    calls = []

    def progress(f: float) -> None:
        calls.append(f)
        if len(calls) >= 2:
            raise jobs.Cancelled()
    start = time.monotonic()
    with pytest.raises(jobs.Cancelled):
        render._run_ffmpeg(cmd, 60, progress)
    assert time.monotonic() - start < 10
    time.sleep(0.3)
    import subprocess
    assert str(tmp_path / "o.mp4") not in subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
