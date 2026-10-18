"""Schnittfassung aus der Datei lesen (ausgelagert aus timeline.py). Nachsichtig: nichts geht verloren, nichts wird
geschrieben."""
from __future__ import annotations

from typing import Any

from . import mix, plan
from . import timeline as tl_


def _loaded_clips(pid: str, raw: Any, audio: bool) -> list[dict]:
    ok = []
    for c in (raw.get("clips") if isinstance(raw, dict) and isinstance(raw.get("clips"), list) else [])[:tl_.MAX_CLIPS]:
        try:
            ok.append(tl_._clip(pid, c, on_load=True, audio=audio))
        except plan.PlanError:
            continue                                     # einzelner kaputter Clip: überspringen, Rest bleibt
    out: list[dict] = []
    for c in sorted(ok, key=lambda c: c["start"]):
        if not out or c["start"] >= tl_._end(out[-1]) - tl_.EPS:  # überlappender Clip (alte/kaputte Datei) wird übersprungen
            out.append(c)
    return out


def from_file(pid: str, raw: dict) -> dict:
    """Kaputte Clips werden übersprungen, Clips mit gelöschtem Medium werden Platzhalter bzw. stumme Tonclips – die
    übrige Arbeit geht nie verloren. Fehlende Tonspuren (Fassungen vor Etappe 5) kommen leer dazu; ungültige
    Mischpult-Werte fallen still auf den Standard zurück. Die Datei bleibt dabei unverändert."""
    rev = raw.get("revision")
    fps = raw.get("fps") if raw.get("fps") in tl_.FPS_ALLOWED else tl_.FPS_DEFAULT
    stored = raw.get("tracks") if isinstance(raw.get("tracks"), list) else []
    by_id: dict[str, Any] = {}
    for i, t in enumerate(stored):
        if isinstance(t, dict):
            by_id.setdefault(t.get("id") or ("V1" if i == 0 else ""), t)
    clips = {tid: _loaded_clips(pid, by_id.get(tid), kind == "audio") for tid, kind in tl_.TRACKS}
    values = {tid: mix.track_values(by_id[tid], strict=False) for tid, _ in tl_.TRACKS if isinstance(by_id.get(tid), dict)}
    out = {"revision": rev if isinstance(rev, int) and not isinstance(rev, bool) and rev >= 0 else 0, "fps": fps,
           "tracks": tl_._tracks(clips, values)}
    return tl_._with_duck(out, raw.get("duck") is not False)
