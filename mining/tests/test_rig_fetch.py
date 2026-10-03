"""Rig-Client E3: Katalog-Schutz, Download-Prüfung, Entpacken, Miner-APIs."""
from __future__ import annotations

import hashlib
import io
import sys
import tarfile
from pathlib import Path

import pytest

RIG_DIR = Path(__file__).resolve().parents[1] / "rig"
if str(RIG_DIR) not in sys.path:
    sys.path.insert(0, str(RIG_DIR))

from hydrahive_rig import catalog, fetch, minerapi

JOB = {"coin": "rvn", "miner": "rigel", "algo": "kawpow", "user": "krxXJK8JJW", "worker": "till-wks", "region": "eu"}


# ---- Katalog-Schutz: Server liefert nur Namen ----
def test_build_matches_command_tested_on_wks():
    s = catalog.build(JOB, "nvidia")
    assert s["args"] == ["-a", "kawpow", "-o", "stratum+tcp://rvn-eu.kryptex.network:7031", "-u", "krxXJK8JJW",
                         "-w", "till-wks", "--no-tui", "--api-bind", f"127.0.0.1:{catalog.API_PORT}"]


@pytest.mark.parametrize("change", [
    {"miner": "evil"}, {"coin": "btc"}, {"algo": "sha256"}, {"user": "a b"}, {"user": "x;reboot"},
    {"worker": "../x"}, {"region": "mars"}, {"coin": "prl", "miner": "rigel", "algo": "pearlhash"},
])
def test_build_rejects_anything_outside_catalog(change):
    with pytest.raises(catalog.JobError):
        catalog.build({**JOB, **change}, "nvidia")


def test_amd_cannot_get_rigel():
    with pytest.raises(catalog.JobError):
        catalog.build(JOB, "amd")


def test_server_and_rig_share_one_catalog():
    from backend import catalog as server_catalog
    assert server_catalog.data() == catalog.data()


# ---- Download + Entpacken ----
def _tgz(entries: dict[str, bytes], extra=None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in entries.items():
            ti = tarfile.TarInfo(name)
            ti.size, ti.mode = len(data), 0o755
            tf.addfile(ti, io.BytesIO(data))
        for ti in extra or []:
            tf.addfile(ti)
    return buf.getvalue()


@pytest.fixture
def fake_miner(monkeypatch):
    blob = _tgz({"rigel-1.23.2-linux/rigel": b"#!/bin/sh\necho hi\n"})
    m = {**catalog.miner("rigel"), "sha256": hashlib.sha256(blob).hexdigest()}
    monkeypatch.setattr(fetch, "miner", lambda name: m)
    return blob


def test_ensure_downloads_checks_and_reuses(tmp_path, fake_miner):
    calls = []

    def dl(url, dest):
        calls.append(url)
        dest.write_bytes(fake_miner)

    exe = fetch.ensure("rigel", tmp_path, download=dl)
    assert exe.is_file() and exe.stat().st_mode & 0o111
    assert fetch.ensure("rigel", tmp_path, download=dl) == exe and len(calls) == 1


def test_ensure_rejects_wrong_hash(tmp_path, fake_miner):
    with pytest.raises(fetch.FetchError, match="sha256_mismatch"):
        fetch.ensure("rigel", tmp_path, download=lambda url, dest: dest.write_bytes(fake_miner + b"x"))
    assert not (tmp_path / "miners" / "rigel-1.23.2").exists()


def test_ensure_redownloads_when_archive_tampered(tmp_path, fake_miner):
    fetch.ensure("rigel", tmp_path, download=lambda u, d: d.write_bytes(fake_miner))
    (tmp_path / "miners" / "rigel-1.23.2" / "archive.tgz").write_bytes(b"manipuliert")
    calls = []
    fetch.ensure("rigel", tmp_path, download=lambda u, d: (calls.append(u), d.write_bytes(fake_miner)))
    assert len(calls) == 1


def test_download_url_must_be_github(tmp_path):
    with pytest.raises(fetch.FetchError, match="url_not_allowed"):
        fetch._download("https://evil.example/x.tgz", tmp_path / "x")


@pytest.mark.parametrize("bad", ["../escape", "/abs/path", "a/../../escape"])
def test_extract_blocks_path_escape(tmp_path, bad):
    arc = tmp_path / "a.tgz"
    arc.write_bytes(_tgz({bad: b"x"}))
    with pytest.raises(fetch.FetchError):
        fetch._safe_extract(arc, tmp_path / "out")


def test_extract_blocks_symlink_out_and_devices(tmp_path):
    link = tarfile.TarInfo("d/link")
    link.type, link.linkname = tarfile.SYMTYPE, "/etc/passwd"
    arc = tmp_path / "a.tgz"
    arc.write_bytes(_tgz({"d/f": b"x"}, [link]))
    with pytest.raises(fetch.FetchError, match="unsafe_link"):
        fetch._safe_extract(arc, tmp_path / "o1")
    dev = tarfile.TarInfo("d/dev")
    dev.type = tarfile.CHRTYPE
    arc.write_bytes(_tgz({"d/f": b"x"}, [dev]))
    with pytest.raises(fetch.FetchError, match="unsafe_type"):
        fetch._safe_extract(arc, tmp_path / "o2")


def test_extract_strips_setuid(tmp_path):
    ti = tarfile.TarInfo("d/suid")
    ti.size, ti.mode = 1, 0o4755
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.addfile(ti, io.BytesIO(b"x"))
    arc = tmp_path / "a.tgz"
    arc.write_bytes(buf.getvalue())
    fetch._safe_extract(arc, tmp_path / "o")
    assert not (tmp_path / "o" / "d" / "suid").stat().st_mode & 0o4000


# ---- Miner-APIs (echte Antworten von tills-master-wks, 03.10.2026) ----
def test_parse_rigel():
    d = {"hashrate": {"kawpow": 21213765.1}, "solution_stat": {"kawpow": {"accepted": 1, "rejected": 0, "invalid": 0}},
         "devices": [{"power_usage": None}]}
    assert minerapi.parse("rigel", d) == {"hashrate": 21213765.1, "accepted": 1, "rejected": 0, "watts": None}


def test_parse_srbminer():
    d = {"algorithms": [{"hashrate": {"gpu": {"gpu0": 8.99e13, "total": 8.99e13}}, "shares": {"accepted": 1, "rejected": 0}}]}
    assert minerapi.parse("srbminer", d)["hashrate"] == 8.99e13


def test_parse_lolminer():
    d = {"Algorithms": [{"Total_Performance": 45.5496, "Performance_Factor": 1000000, "Total_Accepted": 1,
                         "Total_Rejected": 0}], "Workers": [{"Power": 138.737}]}
    r = minerapi.parse("lolminer", d)
    assert r["hashrate"] == pytest.approx(45.5496e6) and r["watts"] == 138.737 and r["accepted"] == 1


def test_parse_empty_and_zero():
    assert minerapi.parse("rigel", {})["hashrate"] is None
    assert minerapi.parse("srbminer", {"algorithms": [{"hashrate": {"gpu": {"total": 0}}}]})["hashrate"] is None


def test_check_members_strips_setuid_itself(tmp_path):
    """Debian 12 (Python 3.11.2) hat keinen data-Filter: dort ist diese Maske die einzige Schicht."""
    ti = tarfile.TarInfo("d/suid")
    ti.size, ti.mode = 1, 0o4777
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.addfile(ti, io.BytesIO(b"x"))
    buf.seek(0)
    with tarfile.open(fileobj=buf, mode="r:gz") as tf:
        (m,) = fetch._check_members(tf, tmp_path)
    assert m.mode == 0o755


def test_parse_rigel_counts_invalid_as_rejected():
    d = {"hashrate": {"kawpow": 1.0}, "solution_stat": {"kawpow": {"accepted": 5, "rejected": 1, "invalid": 2}}}
    assert minerapi.parse("rigel", d)["rejected"] == 3
