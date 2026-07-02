"""Video-Editor — Audio-Mix-Graph für die Nachvertonung (SPEC-AUDIO.md).

Baut die ffmpeg-``-filter_complex``-Argumentliste, die den O-Ton des
geschnittenen Videos mit N Audiospuren mischt:

  pro Clip:  atrim → asetpts → adelay(t_start) → volume(gain) → afade(in/out)
  pro Spur:  amix der Clips + Spur-Gain
  final:     amix(alle aktiven Spuren + O-Ton) → loudnorm (EBU R128)

Reine Kommando-Konstruktion — testbar ohne ffmpeg-Aufruf. Args immer als Liste.

Input-Konvention (vom Aufrufer eingehalten):
  Input 0 = das geschnittene Video (liefert Bild + O-Ton)
  Input 1..N = je eine Audio-Quelldatei pro platziertem Clip (in Clip-Reihenfolge
               über alle aktiven Spuren)
"""
from __future__ import annotations

from pathlib import Path

from .models import EDL, AudioClip, AudioTrack

_LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"


def _ms(seconds: float) -> int:
    return max(0, int(round(seconds * 1000)))


def active_tracks(edl: EDL) -> list[AudioTrack]:
    """Spuren, die tatsächlich in den Mix eingehen: nicht-leer und (bei
    vorhandenem Solo) solo-geschaltet bzw. sonst nicht gemutet."""
    non_empty = [t for t in edl.audio if t.clips]
    solo = [t for t in non_empty if t.solo]
    pool = solo if solo else [t for t in non_empty if not t.mute]
    return pool


def include_original(edl: EDL) -> bool:
    """O-Ton geht ein, außer er ist gemutet ODER es gibt Solo-Audiospuren
    (Solo isoliert die Audiospuren, klassisches DAW-Verhalten)."""
    if edl.original_audio.mute:
        return False
    if any(t.solo for t in edl.audio if t.clips):
        return False
    return True


def _clip_end(clip: AudioClip) -> float:
    """Ende des Clips auf der Timeline (t_start + Ausschnittdauer)."""
    return clip.t_start + (clip.src_end - clip.src_start)


def crossfade_durations(clips: list[AudioClip]) -> dict[str, tuple[float, float]]:
    """Leitet pro Clip effektive (fade_in, fade_out)-Dauern ab.

    Überlappen sich zwei aufeinanderfolgende Clips einer Spur zeitlich, entsteht
    ein Crossfade: der frühere Clip blendet über die Überlappung aus, der spätere
    blendet über dieselbe Zone ein — ``amix`` addiert beide, das Ergebnis ist ein
    gleichmäßiger Übergang. Vom Nutzer gesetzte Fades bleiben Untergrenze (der
    Crossfade kann sie nur verlängern, nie verkürzen).

    Reine Funktion (keine ffmpeg) — separat testbar.
    """
    ordered = sorted(clips, key=lambda c: c.t_start)
    fades: dict[str, tuple[float, float]] = {
        c.id: (c.fade_in, c.fade_out) for c in ordered
    }
    for earlier, later in zip(ordered, ordered[1:]):
        overlap = _clip_end(earlier) - later.t_start
        if overlap <= 0.01:
            continue
        # Überlappung auf die kürzere der beiden Clipdauern begrenzen.
        span = min(
            overlap,
            earlier.src_end - earlier.src_start,
            later.src_end - later.src_start,
        )
        e_in, e_out = fades[earlier.id]
        l_in, l_out = fades[later.id]
        fades[earlier.id] = (e_in, max(e_out, span))
        fades[later.id] = (max(l_in, span), l_out)
    return fades


def _clip_filter(
    in_label: str, clip: AudioClip, out_label: str,
    fades: tuple[float, float] | None = None,
) -> str:
    """Filter-Kette für einen Clip. src_start/end schneiden, an t_start auf der
    Timeline platzieren, Gain + Fades anwenden. ``fades`` überschreibt die
    Clip-Fades (für aus Überlappung abgeleitete Crossfades)."""
    dur = clip.src_end - clip.src_start
    fade_in, fade_out = fades if fades is not None else (clip.fade_in, clip.fade_out)
    steps = [
        f"atrim=start={clip.src_start:.3f}:end={clip.src_end:.3f}",
        "asetpts=PTS-STARTPTS",
    ]
    delay = _ms(clip.t_start)
    if delay > 0:
        # adelay braucht pro Kanal einen Wert; all=1 wendet ihn auf alle an.
        steps.append(f"adelay=delays={delay}:all=1")
    if clip.gain_db != 0.0:
        steps.append(f"volume={clip.gain_db:.2f}dB")
    if fade_in > 0:
        steps.append(f"afade=t=in:st={clip.t_start:.3f}:d={fade_in:.3f}")
    if fade_out > 0:
        fade_start = clip.t_start + dur - fade_out
        steps.append(f"afade=t=out:st={max(0.0, fade_start):.3f}:d={fade_out:.3f}")
    return f"[{in_label}]" + ",".join(steps) + f"[{out_label}]"


def build_filtergraph(edl: EDL) -> tuple[str, int]:
    """Erzeugt den filter_complex-String und die Anzahl benötigter Audio-Inputs
    (= Zahl der Clips in aktiven Spuren). Der O-Ton ist Input 0 ([0:a]).

    Returns (graph, audio_input_count). Bei ``graph == ""`` ist kein Mix nötig.
    """
    if not edl.has_audio_mix():
        return "", 0

    tracks = active_tracks(edl)
    with_orig = include_original(edl)
    parts: list[str] = []
    mix_labels: list[str] = []
    input_idx = 1  # Input 0 ist das Video

    for ti, track in enumerate(tracks):
        clip_labels: list[str] = []
        fades = crossfade_durations(track.clips)
        for ci, clip in enumerate(track.clips):
            out_lbl = f"c{ti}_{ci}"
            parts.append(_clip_filter(f"{input_idx}:a", clip, out_lbl, fades=fades[clip.id]))
            clip_labels.append(out_lbl)
            input_idx += 1
        track_lbl = f"t{ti}"
        if len(clip_labels) == 1:
            inner = f"[{clip_labels[0]}]anull[{track_lbl}]"
        else:
            joined = "".join(f"[{c}]" for c in clip_labels)
            inner = f"{joined}amix=inputs={len(clip_labels)}:normalize=0[{track_lbl}]"
        parts.append(inner)
        if track.gain_db != 0.0:
            gained = f"{track_lbl}g"
            parts.append(f"[{track_lbl}]volume={track.gain_db:.2f}dB[{gained}]")
            track_lbl = gained
        mix_labels.append(track_lbl)

    # O-Ton als weitere Mix-Quelle (mit optionalem Gain).
    if with_orig:
        if edl.original_audio.gain_db != 0.0:
            parts.append(f"[0:a]volume={edl.original_audio.gain_db:.2f}dB[orig]")
            mix_labels.append("orig")
        else:
            mix_labels.append("0:a")

    if not mix_labels:
        return "", input_idx - 1

    joined = "".join(f"[{lbl}]" for lbl in mix_labels)
    if len(mix_labels) == 1:
        parts.append(f"{joined}{_LOUDNORM}[aout]")
    else:
        parts.append(f"{joined}amix=inputs={len(mix_labels)}:normalize=0,{_LOUDNORM}[aout]")

    return ";".join(parts), input_idx - 1


def mix_input_files(edl: EDL, resolve: "callable[[str], Path]") -> list[Path]:
    """Absolute Pfade der Audio-Quelldateien in Input-Reihenfolge (eine pro
    Clip aktiver Spuren). ``resolve`` mappt source_rel → absoluter Pfad."""
    files: list[Path] = []
    for track in active_tracks(edl):
        for clip in track.clips:
            files.append(resolve(clip.source_rel))
    return files
