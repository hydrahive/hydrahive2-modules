"""`incus.run_to_file`: binärer Strom in eine Datei, Größen- und Zeitlimit – mit einem harmlosen Ersatzprogramm
statt echtem incus (kein Container, keine Sonderdateien)."""

from __future__ import annotations

import asyncio
import os
import stat
import textwrap
from pathlib import Path

import pytest
from hydrahive.containers.incus_client import IncusError

from backend import incus


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fake_binary(tmp_path, monkeypatch):
    """Legt ein `incus` an, das je nach erstem Argument Bytes ausgibt, schläft oder fehlschlägt."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "incus"
    script.write_text(textwrap.dedent("""\
        #!/usr/bin/env python3
        import sys, time
        mode = sys.argv[1]
        if mode == "bytes":
            sys.stdout.buffer.write(bytes(range(256)) * 4096)      # 1 MiB, enthält 0x00 und 0xFF
        elif mode == "viel":
            sys.stdout.buffer.write(b"x" * (3 << 20))
        elif mode == "schlaf":
            time.sleep(30)
        elif mode == "fehler":
            sys.stderr.write("kaputt"); sys.exit(3)
        """))
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return script


def test_binaerdaten_kommen_bytegenau_an(tmp_path, fake_binary) -> None:
    out = tmp_path / "x.bin"

    rc, err = run(incus.run_to_file("bytes", out_path=out, timeout=20))

    assert rc == 0 and err == ""
    assert out.read_bytes() == bytes(range(256)) * 4096


def test_fehlercode_und_fehlertext_kommen_zurueck(tmp_path, fake_binary) -> None:
    rc, err = run(incus.run_to_file("fehler", out_path=tmp_path / "x.bin", timeout=20))

    assert rc == 3 and err == "kaputt"


def test_zeitlimit_beendet_den_prozess(tmp_path, fake_binary) -> None:
    with pytest.raises(IncusError) as exc:
        run(incus.run_to_file("schlaf", out_path=tmp_path / "x.bin", timeout=1))

    assert exc.value.code == "incus_timeout"


def test_groessenlimit_bricht_ab(tmp_path, fake_binary) -> None:
    out = tmp_path / "x.bin"

    rc, _err = run(incus.run_to_file("viel", out_path=out, timeout=20, max_bytes=1 << 20))

    assert rc != 0                                           # beendet (SIGXFSZ), nicht „erfolgreich“
    assert out.stat().st_size <= 1 << 20


def test_datei_wird_auch_bei_timeout_geschlossen(tmp_path, fake_binary) -> None:
    out = tmp_path / "x.bin"
    with pytest.raises(IncusError):
        run(incus.run_to_file("schlaf", out_path=out, timeout=1))

    out.unlink()                                             # kein offener Handle mehr nötig
    assert not Path(out).exists()
