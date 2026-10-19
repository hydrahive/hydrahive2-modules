"""ffmpeg darf seinen Elternprozess nicht überleben (Befund 19.10.2026 auf .2: 24 Waisen, je ~97 % CPU, 8 h).

Nachgestellt: kaputtes Bild (PNG-Kopf + Nullbytes, wie test_render_queue) → ffmpeg hängt bei 100 % CPU und gibt nichts
aus. Endet der Python-Prozess (pytest-Abbruch, Mutanten-Lauf mit Zeitlimit, Dienst-Neustart mit KillMode=process), lief
ffmpeg als Waise (ppid=1) weiter; der Wächter-Thread stirbt mit dem Prozess.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from pathlib import Path

from _render_helpers import needs_ffmpeg

ROOT = Path(__file__).resolve().parents[1]


def _alive(pid: int) -> bool:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return stat.rsplit(")", 1)[1].split()[0] != "Z"


@needs_ffmpeg
def test_ffmpeg_stirbt_mit_dem_elternprozess(tmp_path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    pidfile = tmp_path / "pid"
    child = textwrap.dedent(f"""
        import sys, threading, time
        sys.path.insert(0, {str(ROOT)!r})
        from backend import render_ffmpeg
        real = render_ffmpeg.subprocess.Popen
        def spy(*a, **k):
            p = real(*a, **k)
            open({str(pidfile)!r}, "w").write(str(p.pid))
            return p
        render_ffmpeg.subprocess.Popen = spy
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin", "-loop", "1", "-framerate", "25",
               "-t", "2", "-i", {str(img)!r}, "-c:v", "libx264", "-preset", "ultrafast", "-progress", "pipe:1",
               "-nostats", {str(tmp_path / "o.mp4")!r}]
        threading.Thread(target=render_ffmpeg.run, args=(cmd, 2, lambda f: None), daemon=True).start()
        time.sleep(30)
    """)
    proc = subprocess.Popen([sys.executable, "-B", "-c", child])
    pid = 0
    try:
        end = time.monotonic() + 15
        while time.monotonic() < end and not pid:
            if pidfile.exists() and pidfile.read_text().strip():
                pid = int(pidfile.read_text())
            time.sleep(0.05)
        assert pid, "ffmpeg wurde nicht gestartet"
        assert _alive(pid)
        proc.kill()                                   # Elternprozess stirbt hart (wie Zeitlimit/SIGKILL)
        proc.wait(timeout=10)
        end = time.monotonic() + 5
        while time.monotonic() < end and _alive(pid):
            time.sleep(0.05)
        assert not _alive(pid), "ffmpeg läuft als Waise weiter"
    finally:
        proc.kill()
        if pid and _alive(pid):
            subprocess.run(["kill", "-KILL", str(pid)], check=False)
