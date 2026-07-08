"""Atelier — Regie-Film-Mux: Clips zusammenschneiden, Original-Ton behalten und
pro-Szene generierte Musik zeitversetzt leise darunterlegen.

Anders als ``_ffmpeg.build_concat_command`` (Musik ERSETZT den Clip-Ton) erhält
dieser Mux den Original-Ton (Dialoge/Effekte des Video-Modells) und mischt die
Szenen-Musik nur als zusätzliche, leisere Spur (``amix … normalize=0``) an der
Zeitposition der jeweiligen Szene (``adelay``).

Reine Argument-Bauerei — kein ffmpeg-Aufruf hier (testbar ohne Binär).
"""
from __future__ import annotations

import logging
from pathlib import Path

from . import _ffmpeg, film, music, storage

logger = logging.getLogger("hhmod_atelier.director_mux")

_FPS = 24
_MUSIC_GAIN = 0.35  # Musik ~ -9 dB unter dem Original-Ton
_RESOLUTIONS = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080)}


def _norm_chain(idx: int, w: int, h: int, label: str) -> str:
    """Skaliert Video-Input idx auf w×h (Letterbox, kein Verzerren)."""
    return (
        f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={_FPS}[{label}]"
    )


def _clip_audio_chain(idx: int, has_audio: bool, duration: float, silence_idx: int, label: str) -> str:
    """Original-Ton eines Clips normalisiert (44.1 kHz stereo); tonlose Clips
    bekommen Stille passender Länge aus der lavfi-Quelle."""
    dur = max(0.1, duration)
    if has_audio:
        return f"[{idx}:a]aresample=44100,aformat=channel_layouts=stereo[{label}]"
    return f"[{silence_idx}:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[{label}]"


def build_director_mux_command(
    clips: list[Path],
    *,
    out_path: Path,
    width: int,
    height: int,
    clip_meta: list[dict],
    scene_music: list[dict],
    music_gain: float = _MUSIC_GAIN,
) -> list[str]:
    """ffmpeg-Argumentliste für den Regie-Film.

    clips:        Video-Clips in Reihenfolge.
    clip_meta:    je Clip {has_audio: bool, duration: float}.
    scene_music:  Liste {music_path: Path, t_start: float(sek)} — Musik, die ab
                  t_start unter den Film gemischt wird. Leer → nur Original-Ton.
    """
    n = len(clips)
    if n == 0:
        raise ValueError("keine Clips")

    args: list[str] = ["ffmpeg", "-y"]
    for clip in clips:
        args += ["-i", str(clip)]
    # Stille-Quelle für tonlose Clips (Input-Index n).
    silence_idx = n
    args += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

    music = [m for m in scene_music if m.get("music_path")]
    music_base = n + 1
    for m in music:
        args += ["-i", str(m["music_path"])]

    parts: list[str] = [_norm_chain(i, width, height, f"v{i}") for i in range(n)]
    for i in range(n):
        meta = clip_meta[i] if i < len(clip_meta) else {}
        parts.append(_clip_audio_chain(
            i, bool(meta.get("has_audio")), float(meta.get("duration") or 0.0),
            silence_idx, f"a{i}",
        ))

    # Video + Original-Ton concat.
    inter = "".join(f"[v{i}][a{i}]" for i in range(n))
    parts.append(f"{inter}concat=n={n}:v=1:a=1[outv][baseaud]")

    if not music:
        args += ["-filter_complex", ";".join(parts), "-map", "[outv]", "-map", "[baseaud]"]
        args += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac"]
        args += [str(out_path)]
        return args

    # Szenen-Musik: je Stück an t_start verzögern + leiser stellen.
    music_labels: list[str] = []
    for j, m in enumerate(music):
        delay_ms = int(round(max(0.0, float(m.get("t_start") or 0.0)) * 1000))
        lbl = f"m{j}"
        parts.append(
            f"[{music_base + j}:a]adelay={delay_ms}|{delay_ms},"
            f"volume={music_gain}[{lbl}]"
        )
        music_labels.append(lbl)

    mix_inputs = 1 + len(music_labels)
    mix_in = "[baseaud]" + "".join(f"[{lbl}]" for lbl in music_labels)
    # normalize=0: der Original-Ton behält seine Lautstärke, Musik liegt leise drunter.
    # duration=first: Filmlänge = Basis-Ton (Musik wird ggf. abgeschnitten).
    parts.append(f"{mix_in}amix=inputs={mix_inputs}:normalize=0:duration=first[outaud]")

    args += ["-filter_complex", ";".join(parts), "-map", "[outv]", "-map", "[outaud]"]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac"]
    args += [str(out_path)]
    return args


async def mux_screenplay_film(
    project_id: str, *, scenes: list[dict], clips_by_scene: dict[str, list[str]],
    aspect: str, audio_model: str, job: dict,
) -> str:
    """Schneidet die fertigen Regie-Clips zusammen. Pro Szene mit ``music.enabled``
    wird Musik generiert und ab der Szenen-Startzeit leise untergemischt — der
    Original-Ton der Clips (Dialoge/Effekte) bleibt erhalten. Gibt ``films/<name>``.

    Musik-Generierungsfehler sind nicht-fatal (Warnung in ``job['warnings']``).
    """
    root = storage.atelier_root(project_id)

    ordered_clips: list[Path] = []
    clip_meta: list[dict] = []
    scene_music: list[dict] = []
    t_cursor = 0.0
    for scene in scenes:
        rels = clips_by_scene.get(scene["id"]) or []
        if not rels:
            continue
        scene_start = t_cursor
        for rel in rels:
            p = storage.safe_under(root, rel)
            if p is None or not p.is_file():
                continue
            meta = await _ffmpeg.probe_clip(p)
            ordered_clips.append(p)
            clip_meta.append(meta)
            t_cursor += float(meta.get("duration") or 0.0)

        music_cfg = scene.get("music") or {}
        if music_cfg.get("enabled"):
            prompt = (music_cfg.get("prompt") or scene.get("description") or "").strip()
            if prompt:
                try:
                    res = await music.generate_for_project(
                        project_id, {"scene": prompt, "model": audio_model or None},
                    )
                    mp = storage.safe_under(root, res["rel"])
                    if mp is not None and mp.is_file():
                        scene_music.append({"music_path": mp, "t_start": scene_start})
                except Exception as e:  # noqa: BLE001 - Musikfehler bricht den Film nicht ab
                    logger.exception("scene music failed: scene=%s", scene["id"])
                    job.setdefault("warnings", []).append(
                        f"Musik für Szene '{scene.get('title') or ''}': {e}"
                    )

    if not ordered_clips:
        raise RuntimeError("Keine gültigen Clips für den Film.")

    w, h = _RESOLUTIONS.get(aspect, _RESOLUTIONS["16:9"])
    out_name = f"{storage.new_id()}.mp4"
    out_path = storage.films_dir(project_id) / out_name
    args = build_director_mux_command(
        ordered_clips, out_path=out_path, width=w, height=h,
        clip_meta=clip_meta, scene_music=scene_music,
    )
    await film._run_ffmpeg(args)
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise RuntimeError("ffmpeg lieferte keine Ausgabedatei.")
    return f"films/{out_name}"
