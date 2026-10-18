"""Hilfen der 4d-Tests: echte kleine Medien mit ffmpeg erzeugen (Video mit/ohne Ton, Bild), Pfade, Auftrag abwarten."""
from __future__ import annotations

import json
import shutil
import subprocess
import time

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

R = f"{MOD_PREFIX}/projects/{PROJECT_ID}"
needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg fehlt")


def make_video(ws, name: str, seconds: float, *, size: str = "320x240", audio: bool = True) -> str:
    d = ws / "studio/media/videos"
    d.mkdir(parents=True, exist_ok=True)
    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=s={size}:r=24:d={seconds}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=f=440:d={seconds}", "-c:a", "aac", "-shortest"]
    args += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(d / name)]
    subprocess.run(args, check=True, timeout=60)
    (d / f"{name}.json").write_text(json.dumps({"duration": seconds}))
    return f"studio/media/videos/{name}"


def make_image(ws, name: str, size: str = "200x300") -> str:
    d = ws / "studio/media/images"
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=red:s={size}",
                    "-frames:v", "1", str(d / name)], check=True, timeout=30)
    return f"studio/media/images/{name}"


def probe(path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
                          "-of", "json", str(path)], capture_output=True, text=True, timeout=30, check=True).stdout
    return json.loads(out)


def wait_render(client, h, timeout: float = 60.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        jobs = [j for j in client.get(f"{R}/plan/jobs", headers=h).json()["jobs"] if j["kind"] == "render"]
        if jobs and jobs[0]["status"] in ("done", "failed", "cancelled"):
            return jobs[0]
        time.sleep(0.1)
    raise AssertionError("Film nicht fertig geworden")


def put_timeline(client, h, clips: list[dict]) -> dict:
    cur = client.get(f"{R}/timeline", headers=h).json()
    r = client.put(f"{R}/timeline", headers=h, json={"revision": cur["revision"], "fps": 25,
                                                    "tracks": [{"id": "V1", "kind": "video", "clips": clips}]})
    assert r.status_code == 200, r.text
    return r.json()


def clip(kind: str, start: float, t_in: float, t_out: float, media: str = "", label: str = "x") -> dict:
    return {"kind": kind, "start": start, "in": t_in, "out": t_out, "media_rel": media, "scene_id": "", "shot_id": "", "label": label}


def make_audio(ws, name: str, seconds: float, *, freq: int = 880, sub: str = "atelier/audio") -> str:
    d = ws / sub
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f={freq}:d={seconds}",
                    "-ar", "44100", str(d / name)], check=True, timeout=60)
    return f"{sub}/{name}"


def put_tracks(client, h, video: list[dict], voice: list[dict], music: list[dict]) -> dict:
    cur = client.get(f"{R}/timeline", headers=h).json()
    r = client.put(f"{R}/timeline", headers=h, json={"revision": cur["revision"], "fps": 25, "tracks": [
        {"id": "V1", "kind": "video", "clips": video}, {"id": "A1", "kind": "audio", "clips": voice},
        {"id": "A2", "kind": "audio", "clips": music}]})
    assert r.status_code == 200, r.text
    return r.json()


def max_volume(path, start: float, seconds: float) -> float:
    """Lautester Wert (dB) im Ausschnitt; -91 = Stille."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(start), "-t", str(seconds), "-i", str(path),
                          "-af", "volumedetect", "-vn", "-f", "null", "-"], capture_output=True, text=True, timeout=60).stderr
    vals = [float(line.rsplit(":", 1)[1].split()[0]) for line in out.splitlines() if "max_volume" in line]
    return vals[0] if vals else -91.0
