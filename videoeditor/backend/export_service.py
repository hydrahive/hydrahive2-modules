"""Video-Editor — Export: Hybrid-Rendering mit Output-Profil + Live-Fortschritt.

Pro Clip: 'copy' nur wenn src_start auf einem Keyframe liegt UND das Ziel-Profil
kein Re-Encode erzwingt (Skalierung/Codec-Wechsel/Qualitätsziel). Sonst
frame-genaues Re-Encode. Erzwingt das Profil global Re-Encode, müssen ALLE
Clips transkodieren (concat-Demuxer braucht homogene Streams).

Segmente einzeln rendern → per concat-Demuxer verlustfrei zusammenfügen.
Fortschritt: Summe der Clip-Dauern = Nenner; ffmpeg -progress liefert out_time_us
pro Clip → an progress_cb(percent) gemeldet.
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Awaitable, Callable

from ._audio_mix import build_filtergraph, mix_input_files
from ._ffmpeg import FFmpegError
from ._segment_args import segment_args
from .models import Clip, EDL
from .render_presets import OutputProfile, output_forces_reencode

_KEYFRAME_TOLERANCE_SEC = 1 / 24
ProgressCb = Callable[[float], Awaitable[None]] | None


def _needs_reencode(clip: Clip, keyframes: list[float], profile_forces: bool) -> bool:
    if profile_forces:
        return True
    if clip.mode == "reencode":
        return True
    # 'copy' nur wenn src_start wirklich auf einem Keyframe liegt
    return not any(abs(k - clip.src_start) <= _KEYFRAME_TOLERANCE_SEC for k in keyframes)


async def _run_progress(args: list[str], clip_dur: float, done: float, total: float, cb: ProgressCb) -> None:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdout is not None
    async for line in proc.stdout:
        text = line.decode("utf-8", "replace").strip()
        if text.startswith("out_time_us=") and cb is not None and total > 0:
            try:
                sec = int(text.split("=", 1)[1] or 0) / 1_000_000.0
            except ValueError:
                continue
            pct = (done + min(sec, clip_dur)) / total
            await cb(max(0.0, min(pct, 0.999)))
    rc = await proc.wait()
    if rc != 0:
        err = (await proc.stderr.read()).decode("utf-8", "replace") if proc.stderr else ""
        raise FFmpegError(err[-400:])


async def render_export(
    src: Path, clips: list[Clip], dst: Path, *,
    keyframes: list[float], profile: OutputProfile | None = None,
    source_meta: dict | None = None, progress_cb: ProgressCb = None,
    edl: EDL | None = None, resolve_audio: "Callable[[str], Path] | None" = None,
) -> None:
    if not clips:
        raise FFmpegError("Export ohne Clips.")
    profile = profile or OutputProfile()
    forces, _reason = output_forces_reencode(profile, source_meta)
    source_codec = (source_meta or {}).get("video_codec")
    total = sum(c.src_end - c.src_start for c in clips)
    container = "mp4"
    do_mix = edl is not None and edl.has_audio_mix() and resolve_audio is not None

    with tempfile.TemporaryDirectory(prefix="videoeditor-export-") as tmpdir:
        tmp = Path(tmpdir)
        segment_paths: list[Path] = []
        done = 0.0
        for i, clip in enumerate(clips):
            seg = tmp / f"seg-{i:04d}.{container}"
            reencode = _needs_reencode(clip, keyframes, forces)
            args = segment_args(
                src, clip, seg, reencode=reencode, profile=profile,
                source_codec=source_codec, progress=True,
            )
            await _run_progress(args, clip.src_end - clip.src_start, done, total, progress_cb)
            if not seg.is_file():
                raise FFmpegError(f"Segment {i} nicht erzeugt.")
            segment_paths.append(seg)
            done += clip.src_end - clip.src_start

        # Concat der Video-Segmente. Ohne Audio-Mix direkt nach dst; mit Mix in
        # eine Zwischendatei, die dann als Input 0 in den Mix-Schritt geht.
        cut_video = (tmp / f"cut.{container}") if do_mix else dst
        concat_list = tmp / "concat.txt"
        concat_list.write_text("\n".join(f"file '{p.as_posix()}'" for p in segment_paths) + "\n")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", str(cut_video),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0 or not cut_video.is_file():
            raise FFmpegError(err.decode("utf-8", "replace")[-400:])

        if do_mix:
            assert edl is not None and resolve_audio is not None
            await _mux_audio(cut_video, edl, resolve_audio, dst)
            if not dst.is_file():
                raise FFmpegError("Audio-Mix-Ausgabe nicht erzeugt.")

        if progress_cb is not None:
            await progress_cb(1.0)


async def _mux_audio(
    cut_video: Path, edl: EDL, resolve_audio: "Callable[[str], Path]", dst: Path,
) -> None:
    """Mischt O-Ton + Audiospuren in einem ffmpeg-Schritt über den
    filter_complex-Graph. Bild wird kopiert (kein Video-Reencode)."""
    graph, _n = build_filtergraph(edl)
    if not graph:
        # Sollte nicht passieren (do_mix prüft has_audio_mix), aber sicher ist sicher.
        raise FFmpegError("Leerer Audio-Mix-Graph.")
    audio_inputs = mix_input_files(edl, resolve_audio)
    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(cut_video)]
    for f in audio_inputs:
        args += ["-i", str(f)]
    args += [
        "-filter_complex", graph,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(dst),
    ]
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise FFmpegError(err.decode("utf-8", "replace")[-400:])
