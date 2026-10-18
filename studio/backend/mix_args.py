"""Ton-Teil des Filtergraphen der Ausgabe (Spec „Bauplan Etappe 5“, 5a + 5b Mischpult). Rein, ohne ffmpeg-Aufruf.

Je Tonclip: Ausschnitt → Blenden (afade, Zeit im Clip) → Lautstärke (Clip + Spur) → an seine Stelle (adelay).
Ducking: die Musikclips laufen über einen gemeinsamen Bus mit der festen Kurve aus mix.duck_expr (t = Zeit im Film).
Zum Schluss mit dem Originalton (Spur V1: Lautstärke, stumm) mischen, normalize=0, alimiter.
Ohne Mischpult-Einstellungen entsteht genau der Graph aus 5a.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .mix import Mixer, duck_expr, duck_spans

AUDIO = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"


def _track(p: dict) -> str:
    return p.get("track") or "A2"


def build(parts: list[dict], base: Path, n_in: int, mx: Mixer, media: Callable[[Path, str], str]) -> tuple[list[str], list[str]]:
    """Liefert (Eingabe-Argumente, Graph-Zeilen). Die Zeilen lesen `[a0]` (Ton des Bildteils) und schreiben `[a]`.
    Leere Listen = nichts zu tun, dann schreibt der Bildteil direkt `[a]`."""
    keep = [p for p in parts if mx.hears(_track(p))]
    orig_gain, orig_on = mx.track_gain("V1"), mx.hears("V1")
    if not keep and orig_on and not orig_gain:
        return [], []
    graph: list[str] = []
    src = "[a0]"
    if not orig_on or orig_gain:
        out = "[a]" if not keep else "[o]"
        graph.append(f"[a0]volume={'0' if not orig_on else f'{orig_gain:.2f}dB'}{out}")
        if not keep:
            return [], graph
        src = "[o]"
    args: list[str] = []
    for k, p in enumerate(keep):
        sec = p["seconds"]
        d = f"{sec:.3f}"
        args += ["-ss", f"{p['in']:.3f}", "-t", d, "-i", media(base, p["media"])]
        chain = f"[{n_in + k}:a]{AUDIO},atrim=duration={d},asetpts=PTS-STARTPTS"
        if p.get("fade_in"):
            chain += f",afade=t=in:st=0:d={p['fade_in']:.3f}"
        if p.get("fade_out"):
            chain += f",afade=t=out:st={sec - p['fade_out']:.3f}:d={p['fade_out']:.3f}"
        gain = float(p.get("gain_db") or 0) + mx.track_gain(_track(p))
        if gain:
            chain += f",volume={gain:.2f}dB"
        graph.append(chain + f",adelay={round(p['start'] * 1000)}:all=1[m{k}]")
    voice = [k for k, p in enumerate(keep) if _track(p) == "A1"]
    music = [k for k, p in enumerate(keep) if _track(p) != "A1"]
    inputs = [src] + [f"[m{k}]" for k in range(len(keep))]
    if mx.duck and voice and music:
        bus = f"[m{music[0]}]"
        if len(music) > 1:
            graph.append(f"{''.join(f'[m{k}]' for k in music)}amix=inputs={len(music)}:normalize=0:duration=longest[mb]")
            bus = "[mb]"
        spans = duck_spans([[keep[k]["start"], keep[k]["start"] + keep[k]["seconds"]] for k in voice])
        graph.append(f"{bus}volume='{duck_expr(spans)}':eval=frame[mus]")
        inputs = [src] + [f"[m{k}]" for k in voice] + ["[mus]"]
    # duration=first: die Länge gibt der Bildteil vor (er ist per pad_to schon lang genug)
    graph.append(f"{''.join(inputs)}amix=inputs={len(inputs)}:normalize=0:duration=first,alimiter=limit=0.95[a]")
    return args, graph
