"""Hördatei für die Untertitel (Spec „Bauplan 6b“): Originalton der Videos + Spur „Sprache“, ohne Musik und ohne
Mischpult, Mono 16 kHz AAC. Reine Funktion; Ausführen über render._run_ffmpeg."""
from __future__ import annotations

from pathlib import Path

from . import render_args

VOICE = "aresample=16000,aformat=sample_fmts=fltp:channel_layouts=mono"


def command(segs: list[dict], voice: list[dict], base: Path, out: Path) -> list[str]:
    """`segs`: Bildabschnitte (render_args.segments, mit has_audio); `voice`: Teile der Spur „Sprache“ (audio_parts)."""
    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin"]
    graph: list[str] = []
    pieces: list[str] = []
    n = 0
    for i, s in enumerate(segs):
        d = f"{s['seconds']:.3f}"
        if s["kind"] == "video" and s.get("has_audio", True):
            args += ["-ss", f"{s['in']:.3f}", "-t", d, "-i", render_args._media(base, s["media"])]
            graph.append(f"[{n}:a]{VOICE},atrim=duration={d},apad,atrim=duration={d},asetpts=PTS-STARTPTS[s{i}]")
        else:
            args += ["-f", "lavfi", "-t", d, "-i", "anullsrc=r=16000:cl=mono"]
            graph.append(f"[{n}:a]{VOICE},asetpts=PTS-STARTPTS[s{i}]")
        n += 1
        pieces.append(f"[s{i}]")
    graph.append(f"{''.join(pieces)}concat=n={len(segs)}:v=0:a=1[orig]")
    mix = ["[orig]"]
    for k, p in enumerate(voice):
        d = f"{p['seconds']:.3f}"
        args += ["-ss", f"{p['in']:.3f}", "-t", d, "-i", render_args._media(base, p["media"])]
        graph.append(f"[{n}:a]{VOICE},atrim=duration={d},asetpts=PTS-STARTPTS,adelay={round(p['start'] * 1000)}:all=1[v{k}]")
        mix.append(f"[v{k}]")
        n += 1
    out_label = "[orig]"
    if len(mix) > 1:
        graph.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.95[a]")
        out_label = "[a]"
    args += ["-filter_complex", ";".join(graph), "-map", out_label, "-vn", "-c:a", "aac", "-b:a", "32k", "-ac", "1", "-ar", "16000",
             "-progress", "pipe:1", "-nostats", str(out)]
    return args
