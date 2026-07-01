"""Video-Editor — Export: Hybrid-Rendering (copy wo möglich, reencode wo nötig).

Pro Clip wird geprüft, ob src_start auf einem Keyframe liegt (Toleranz
1 Frame). Nur dann ist ``-c copy`` für dieses Segment wirklich verlustfrei UND
korrekt (stream-copy schneidet immer am nächsten Keyframe VOR dem Startpunkt —
liegt src_start nicht exakt darauf, verschiebt sich der Clip-Anfang). Sonst
wird das Segment neu kodiert (frame-genau).

Segmente werden einzeln als temporäre .mp4 gerendert, dann per ffmpeg
concat-Demuxer verlustfrei aneinandergehängt (kein erneutes Re-Encoding beim
Zusammenfügen).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .models import Clip
from ._ffmpeg import FFmpegError, run as _run

_KEYFRAME_TOLERANCE_SEC = 1 / 24  # ~1 Frame bei 24fps als Sicherheitsmarge


def resolve_modes(clips: list[Clip], keyframes: list[float]) -> list[Clip]:
    """Downgrade 'copy'→'reencode' für Clips, deren src_start nicht auf
    einem Keyframe liegt — verhindert stillen Zeitversatz im Export."""
    resolved = []
    for c in clips:
        mode = c.mode
        if mode == "copy":
            on_keyframe = any(abs(k - c.src_start) <= _KEYFRAME_TOLERANCE_SEC for k in keyframes)
            if not on_keyframe:
                mode = "reencode"
        resolved.append(Clip(id=c.id, src_start=c.src_start, src_end=c.src_end, mode=mode))
    return resolved


async def _render_segment(src: Path, clip: Clip, out: Path) -> None:
    dur = clip.src_end - clip.src_start
    if clip.mode == "copy":
        args = [
            "ffmpeg", "-y", "-ss", f"{clip.src_start:.3f}", "-i", str(src),
            "-t", f"{dur:.3f}", "-c", "copy", "-avoid_negative_ts", "make_zero",
            str(out),
        ]
    else:
        args = [
            "ffmpeg", "-y", "-ss", f"{clip.src_start:.3f}", "-i", str(src),
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k",
            str(out),
        ]
    rc, _, err = await _run(*args)
    if rc != 0 or not out.is_file():
        raise FFmpegError(err.decode("utf-8", "replace")[-400:])


async def render_export(src: Path, clips: list[Clip], dst: Path, *, keyframes: list[float]) -> None:
    if not clips:
        raise FFmpegError("Export ohne Clips.")
    resolved = resolve_modes(clips, keyframes)

    with tempfile.TemporaryDirectory(prefix="videoeditor-export-") as tmpdir:
        tmp = Path(tmpdir)
        segment_paths: list[Path] = []
        for i, clip in enumerate(resolved):
            seg = tmp / f"seg-{i:04d}.mp4"
            await _render_segment(src, clip, seg)
            segment_paths.append(seg)

        concat_list = tmp / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in segment_paths) + "\n"
        )
        args = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", str(dst),
        ]
        rc, _, err = await _run(*args)
        if rc != 0 or not dst.is_file():
            raise FFmpegError(err.decode("utf-8", "replace")[-400:])
