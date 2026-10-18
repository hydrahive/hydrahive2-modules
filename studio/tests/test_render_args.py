"""Studio 4d: Bau der ffmpeg-Argumente als reine Funktion (studio/SPEC.md „Bauplan 4d“). Ohne ffmpeg-Aufruf."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend import render_args as ra

BASE = Path("/proj")


def _c(kind, start, t_in, t_out, media="", label="x"):
    return {"kind": kind, "start": start, "in": t_in, "out": t_out, "media_rel": media, "label": label}


@pytest.mark.parametrize(("aspect", "size"), [("16:9", (1280, 720)), ("9:16", (720, 1280)), ("1:1", (1080, 1080)),
                                              ("4:3", (960, 720)), ("21:9", (1680, 720)), ("unsinn", (1280, 720))])
def test_size_from_aspect(aspect, size) -> None:
    assert ra.frame_size(aspect) == size


def test_segments_with_gaps_and_kinds() -> None:
    # Video 0–2 (Ausschnitt 1–3), Lücke 2–3, Bild 3–8, direkt danach Platzhalter 8–10
    clips = [_c("video", 0, 1, 3, "v.mp4"), _c("image", 3, 0, 5, "b.png"), _c("placeholder", 8, 0, 2, label="Sturm · Shot 2")]
    segs = ra.segments(clips, exists=lambda rel: True)
    assert [(s["kind"], s["seconds"]) for s in segs] == [("video", 2), ("gap", 1), ("image", 5), ("placeholder", 2)]
    assert ra.total_seconds(segs) == 10
    assert segs[0]["in"] == 1 and segs[3]["label"] == "Sturm · Shot 2"


def test_missing_file_becomes_placeholder() -> None:
    segs = ra.segments([_c("video", 0, 0, 3, "weg.mp4", label="A"), _c("image", 3, 0, 2, "da.png")], exists=lambda rel: rel == "da.png")
    assert [s["kind"] for s in segs] == ["placeholder", "image"]
    assert segs[0]["label"] == "A" and ra.missing_count(segs) == 1
    loaded = ra.segments([_c("placeholder", 0, 0, 2, label="B") | {"missing": True}, _c("placeholder", 2, 0, 1)], exists=lambda r: True)
    assert ra.missing_count(loaded) == 1                                               # beim Laden schon fehlend


def test_command_shape() -> None:
    segs = [{"kind": "video", "seconds": 2, "in": 1, "media": "v.mp4", "has_audio": True},
            {"kind": "image", "seconds": 5, "media": "b.png"},
            {"kind": "placeholder", "seconds": 2, "label": "Sturm: 'Shot' 2 \\ 100%"},
            {"kind": "gap", "seconds": 1}]
    cmd = ra.command(segs, BASE, Path("/out/x.mp4"), size=(1280, 720), fps=25, text_files={2: Path("/tmp/r 1/2.txt")})
    assert cmd[0] == "ffmpeg" and cmd[-1] == "/out/x.mp4" and "-filter_complex" in cmd
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "concat=n=4:v=1:a=1" in graph
    assert graph.count("scale=1280:720:force_original_aspect_ratio=decrease") == 2       # Video + Bild eingepasst
    assert graph.count("pad=1280:720") == 2
    assert "fps=25" in graph and "drawtext=" in graph
    # Nutzertext steht nie im Graphen, nur der Pfad der Textdatei (in '…', ':' maskiert)
    assert "drawtext=textfile='/tmp/r 1/2.txt':expansion=none" in graph and "Sturm" not in graph
    ins = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-i"]
    assert ins[0] == "/proj/v.mp4" and ins[1] == "/proj/b.png"
    assert cmd[cmd.index("/proj/v.mp4") - 5: cmd.index("/proj/v.mp4")] == ["-ss", "1.000", "-t", "2.000", "-i"]
    for want in (["-c:v", "libx264"], ["-c:a", "aac"], ["-movflags", "+faststart"], ["-pix_fmt", "yuv420p"]):
        i = cmd.index(want[0])
        assert cmd[i:i + 2] == want


def test_video_without_audio_gets_silence() -> None:
    segs = [{"kind": "video", "seconds": 2, "in": 0, "media": "v.mp4", "has_audio": False}]
    graph = ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25)
    g = graph[graph.index("-filter_complex") + 1]
    assert "anullsrc" in " ".join(graph) and "[0:a]" not in g


def test_no_shell_and_no_path_escape() -> None:
    segs = [{"kind": "image", "seconds": 1, "media": "../../etc/passwd"}]
    with pytest.raises(ValueError):
        ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25)


def test_time_limit() -> None:
    assert ra.time_limit(10) == 120
    assert ra.time_limit(100) == 400


def test_label_text_one_line() -> None:
    assert ra.label_text("  a\n b\t c ") == "a b c"
    assert len(ra.label_text("x" * 500)) == 120
    assert ra.label_text("") == ""


def test_no_text_file_no_drawtext() -> None:
    cmd = ra.command([{"kind": "placeholder", "seconds": 1, "label": "x"}], BASE, Path("/o.mp4"), size=(320, 240), fps=25)
    assert "drawtext" not in cmd[cmd.index("-filter_complex") + 1]


@pytest.mark.parametrize(("size", "chars"), [((720, 1280), 120), ((1280, 720), 120), ((1080, 1080), 60), ((960, 720), 30)])
def test_text_fits_the_frame(size, chars) -> None:
    """Schrift nach der kürzeren Seite; Zeilen so umbrochen, dass sie in 90 % der Breite passen (DejaVu ≈ 0,6 × Größe)."""
    fs = ra.font_size(size)
    assert 18 <= fs <= min(size) // 18 + 1
    lines = ra.wrap(ra.label_text("Wort " * (chars // 5)), size).split("\n")
    assert all(len(line) * fs * 0.6 <= size[0] * 0.9 for line in lines)
    assert len(lines) <= 4


def test_wrap_keeps_short_text_on_one_line() -> None:
    assert ra.wrap("Der Sturm · Shot 2", (720, 1280)) == "Der Sturm · Shot 2"


def test_wrap_long_word_and_too_many_lines() -> None:
    size = (720, 1280)
    per_line = int(720 * 0.9 / (ra.font_size(size) * 0.6))
    long = ra.wrap("X" * (per_line * 2 + 3), size).split("\n")
    assert [len(x) for x in long] == [per_line, per_line, 3]                        # überlanges Wort hart geteilt
    many = ra.wrap("abc " * 200, size).split("\n")
    assert len(many) == 4 and many[-1].endswith("…") and len(many[-1]) <= per_line   # Rest mit …
