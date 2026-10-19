"""Film als MP4 (Spec „Bauplan 4d“): Schnittfassung → Abschnitte → ffmpeg-Argumente. Reine Funktionen, testbar ohne
ffmpeg. Argumente immer als Liste (keine Shell). Vorbild für die Einzelschritte: videoeditor/backend/_segment_args.py
(eigene Fassung, Module importieren nicht übereinander).

Ein Filtergraph mit concat: jeder Abschnitt wird auf dieselbe Größe, Bildrate und Tonform gebracht, dann aneinander
gehängt. Video/Bild eingepasst mit schwarzem Rand, Platzhalter und Lücken als schwarze Fläche, Ton Stille.
Tonspuren (Etappe 5): jeder Tonclip wird ausgeschnitten, an seine Stelle verzögert (adelay) und mit dem Ton des Bildes
gemischt (amix ohne Normalisieren, danach alimiter). Idee wie videoeditor/backend/_audio_mix.py, eigene Fassung.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from . import mix_args
from .mix import Mixer
from .subtitle_format import subtitle_args

SIZES = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080), "4:3": (960, 720), "21:9": (1680, 720)}
DEFAULT_SIZE = SIZES["16:9"]
EPS = 1e-3                     # kleinere Lücken (Gleitkomma-Reste beim Aneinanderstoßen) zählen nicht
AUDIO = mix_args.AUDIO


def frame_size(aspect: str) -> tuple[int, int]:
    return SIZES.get(aspect, DEFAULT_SIZE)


def time_limit(seconds: float) -> int:
    """Zeitgrenze fürs Rendern: Filmlänge × 4, mindestens 120 s."""
    return max(120, int(seconds * 4))


def segments(clips: list[dict], *, exists: Callable[[str], bool]) -> list[dict]:
    """Clips (nach start sortiert) → Abschnitte mit Lücken. Fehlt die Datei eines Clips, wird er zum Platzhalter."""
    out: list[dict] = []
    t = 0.0
    for c in sorted(clips, key=lambda x: x["start"]):
        if c["start"] - t > EPS:
            out.append({"kind": "gap", "seconds": round(c["start"] - t, 3)})
        seconds = round(c["out"] - c["in"], 3)
        kind, media = c["kind"], c.get("media_rel") or ""
        if kind in ("video", "image") and not exists(media):
            out.append({"kind": "placeholder", "seconds": seconds, "label": c.get("label") or "", "missing": True})
        elif kind == "video":
            out.append({"kind": "video", "seconds": seconds, "in": c["in"], "media": media})
        elif kind == "image":
            out.append({"kind": "image", "seconds": seconds, "media": media})
        else:                                   # Platzhalter; „missing“ = Medium schon beim Laden der Fassung weg
            out.append({"kind": "placeholder", "seconds": seconds, "label": c.get("label") or "",
                        **({"missing": True} if c.get("missing") else {})})
        t = max(t, c["start"] + seconds)
    return out


def audio_parts(clips: list[dict], *, exists: Callable[[str], bool]) -> list[dict]:
    """Tonclips aller Tonspuren → Teile zum Mischen (nach Start). Ohne Datei (gelöscht) → weggelassen = Stille.
    `track` (A1/A2) und die Mischpult-Werte des Clips (5b) werden mitgegeben, falls vorhanden."""
    out = []
    for c in sorted(clips, key=lambda x: x["start"]):
        media = c.get("media_rel") or ""
        if c.get("missing") or not media or not exists(media):
            continue
        part = {"start": c["start"], "in": c["in"], "seconds": round(c["out"] - c["in"], 3), "media": media}
        part.update({k: c[k] for k in ("track", "gain_db", "fade_in", "fade_out") if c.get(k)})
        out.append(part)
    return out


def audio_end(parts: list[dict]) -> float:
    return round(max((p["start"] + p["seconds"] for p in parts), default=0.0), 3)


def pad_to(segs: list[dict], seconds: float) -> list[dict]:
    """Reicht der Ton über das letzte Bild hinaus, wird der Film bis dahin schwarz verlängert (Ton nicht abschneiden)."""
    rest = round(seconds - total_seconds(segs), 3)
    return [*segs, {"kind": "gap", "seconds": rest}] if rest > EPS else segs


def missing_count(segs: list[dict]) -> int:
    return sum(1 for s in segs if s.get("missing"))


def total_seconds(segs: list[dict]) -> float:
    return round(sum(s["seconds"] for s in segs), 3)


def label_text(label: str) -> str:
    """Text der Platzhalter-Karte: eine Zeile, höchstens 120 Zeichen. Er kommt über eine Datei (textfile=) in den Film,
    deshalb ist keine Maskierung für den Filtergraphen nötig (Nutzertext mit : ' % [ ] \\ ; , war sonst fehleranfällig)."""
    return " ".join((label or "").split())[:120]


CHAR_WIDTH = 0.6                # mittlere Zeichenbreite von DejaVu Sans im Verhältnis zur Schriftgröße
MAX_LINES = 4


def font_size(size: tuple[int, int]) -> int:
    """Schriftgröße nach der kürzeren Seite (hochkant sonst viel zu groß)."""
    return max(18, min(size) // 20)


def wrap(text: str, size: tuple[int, int]) -> str:
    """Wortweise umbrechen, sodass jede Zeile in 90 % der Breite passt; höchstens MAX_LINES Zeilen (Rest mit …)."""
    per_line = max(8, int(size[0] * 0.9 / (font_size(size) * CHAR_WIDTH)))
    lines: list[str] = []
    for word in text.split():
        while len(word) > per_line:                     # überlange Wörter hart teilen
            lines.append(word[:per_line])
            word = word[per_line:]
        if lines and len(lines[-1]) + 1 + len(word) <= per_line:
            lines[-1] += " " + word
        elif word:
            lines.append(word)
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES]
        lines[-1] = lines[-1][: per_line - 1].rstrip() + "…"
    return "\n".join(lines)


def _graph_path(p: Path) -> str:
    """Pfad als Wert im Filtergraphen: in '…' und mit maskierten \\ ' : (eigener, fester Ordner – kein Nutzertext)."""
    v = str(p).replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
    return f"'{v}'"


def _media(base: Path, rel: str) -> str:
    p = (base / rel).resolve()
    if not rel or rel.startswith("/") or not p.is_relative_to(base.resolve()):
        raise ValueError("Medium außerhalb des Projekts")
    return str(p)


def command(segs: list[dict], base: Path, out: Path, *, size: tuple[int, int], fps: int,
            text_files: dict[int, Path] | None = None, audio: list[dict] | None = None, mixer: Mixer | None = None,
            subtitles: list[dict] | None = None, default_language: str = "") -> list[str]:
    """`text_files`: je Platzhalter-Abschnitt (Index) eine Datei mit label_text(); ohne Datei keine Schrift.
    `audio`: Teile aus audio_parts(); `mixer`: Mischpult (5b). Ohne beides bleibt der Graph genau wie in 4d."""
    w, h = size
    text_files = text_files or {}
    fit = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
           f"setsar=1,fps={fps},format=yuv420p")
    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin"]
    graph: list[str] = []
    pairs: list[str] = []
    n_in = 0
    for i, s in enumerate(segs):
        d = f"{s['seconds']:.3f}"
        if s["kind"] == "video":
            args += ["-ss", f"{s['in']:.3f}", "-t", d, "-i", _media(base, s["media"])]
            graph.append(f"[{n_in}:v]{fit},trim=duration={d},setpts=PTS-STARTPTS[v{i}]")
            if s.get("has_audio", True):
                graph.append(f"[{n_in}:a]{AUDIO},atrim=duration={d},apad,atrim=duration={d},asetpts=PTS-STARTPTS[a{i}]")
            n_in += 1
        elif s["kind"] == "image":
            args += ["-loop", "1", "-framerate", str(fps), "-t", d, "-i", _media(base, s["media"])]
            graph.append(f"[{n_in}:v]{fit},trim=duration={d},setpts=PTS-STARTPTS[v{i}]")
            n_in += 1
        else:
            args += ["-f", "lavfi", "-t", d, "-i", f"color=c=black:s={w}x{h}:r={fps}"]
            # expansion=none: %{…} im Nutzertext nicht auswerten (sonst Warnung bzw. eingesetzte Werte)
            text = (f",drawtext=textfile={_graph_path(text_files[i])}:expansion=none:fontcolor=white:fontsize={font_size(size)}"
                    ":line_spacing=8:x=(w-tw)/2:y=(h-th)/2") if i in text_files else ""
            graph.append(f"[{n_in}:v]setsar=1{text},format=yuv420p[v{i}]")
            n_in += 1
        if not (s["kind"] == "video" and s.get("has_audio", True)):
            args += ["-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo"]
            graph.append(f"[{n_in}:a]{AUDIO},asetpts=PTS-STARTPTS[a{i}]")
            n_in += 1
        pairs.append(f"[v{i}][a{i}]")
    extra_args, extra_graph = mix_args.build(audio or [], base, n_in, mixer or Mixer(), _media)
    graph.append(f"{''.join(pairs)}concat=n={len(segs)}:v=1:a=1[v][{'a0' if extra_graph else 'a'}]")
    args += extra_args
    graph += extra_graph
    sub_in, sub_map = subtitle_args(subtitles or [], n_in + extra_args.count("-i"), default_language)
    args += sub_in
    args += ["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]", *sub_map,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", str(fps),
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart",
             "-progress", "pipe:1", "-nostats", str(out)]
    return args
