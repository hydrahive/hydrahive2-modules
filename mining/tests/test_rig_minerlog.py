"""Miner-Log sichtbar machen: SRBMiner schreibt ohne Terminal nichts nach stdout.

Anlass: Auf Kugelfangs Rechnern brach SRBMiner bei Pearl ab (watchdog:exited),
miner.log war leer, der Grund unsichtbar.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rig"))

from hydrahive_rig import catalog, runner
from tests.test_rig_runner import JOB, FakeProc

SRB = {**JOB, "coin": "prl", "miner": "srbminer", "algo": "pearlhash"}


def test_srbminer_writes_own_logfile():
    spec = catalog.build(SRB, "nvidia")
    assert spec["log_file"] == "srbminer.log"
    assert spec["log_args"] == ["--log-file", "{logfile}", "--log-file-mode", "1"]   # 1 = anhängen


def test_other_miners_have_no_logfile_flag():
    for miner, algo, coin in (("rigel", "kawpow", "rvn"), ("lolminer", "AUTOLYKOS2", "erg")):
        spec = catalog.build({**JOB, "coin": coin, "miner": miner, "algo": algo}, "nvidia")
        assert "--log-file" not in spec["args"] and spec["log_file"] is None and spec["log_args"] == []


def test_mixed_rig_logfile_per_group():
    a = catalog.build(SRB, "amd", mixed=True, group="amd")
    n = catalog.build(SRB, "nvidia", mixed=True, group="nvidia")
    assert a["log_file"] != n["log_file"]


class _H:
    def __init__(self, tmp_path, monkeypatch):
        self.t, self.argv = 1000.0, []
        monkeypatch.setattr(runner.os, "killpg", lambda pid, sig: None)
        self.r = runner.Runner(tmp_path, "nvidia", clock=lambda: self.t, spawn=self._spawn,
                               ensure=lambda name, d: tmp_path / "bin" / name, read_api=lambda kind, port: None)

    def _spawn(self, argv, **kw):
        self.argv.append(argv)
        return FakeProc()


def test_runner_passes_absolute_logfile_in_state_dir(tmp_path, monkeypatch):
    h = _H(tmp_path, monkeypatch)
    h.r.apply({"action": "benchmark", "job": SRB})
    args = h.argv[0]
    path = Path(args[args.index("--log-file") + 1])
    assert path.is_absolute() and path.parent == tmp_path and path.name == "srbminer.log"


def test_give_up_logs_last_miner_lines(tmp_path, monkeypatch, caplog):
    h = _H(tmp_path, monkeypatch)
    (tmp_path / "srbminer.log").write_text("".join(f"Zeile {i}\n" for i in range(50))
                                          + "\x1b[31mCUDA error: out of memory\x1b[0m\n")
    h.r.apply({"action": "benchmark", "job": SRB})
    with caplog.at_level(logging.ERROR, logger="hydrahive_rig"):
        for _ in range(runner.MAX_RESTARTS):
            h.r.proc.rc = 1
            h.r.tick(None)
    lines = [r.getMessage() for r in caplog.records]
    assert any(m.endswith("srbminer: CUDA error: out of memory") for m in lines)       # ohne Farbcodes
    assert not any("\x1b" in m or "[31m" in m for m in lines)
    text = caplog.text
    assert "Zeile 49" in text and "Zeile 10" not in text           # nur die letzten Zeilen


def test_give_up_without_logfile_still_works(tmp_path, monkeypatch, caplog):
    h = _H(tmp_path, monkeypatch)
    h.r.apply({"action": "mine", "job": JOB})                         # rigel: Ausgabe in miner.log
    (tmp_path / "miner.log").write_bytes(b"rigel: unsupported GPU\n" + b"\xff\xfe kaputt\n")
    with caplog.at_level(logging.ERROR, logger="hydrahive_rig"):
        for _ in range(runner.MAX_RESTARTS):
            h.r.proc.rc = 1
            h.r.tick(None)
    assert "unsupported GPU" in caplog.text and h.r.error == "watchdog:exited"


@pytest.mark.parametrize("size", [0, 5 * 1024 * 1024])
def test_tail_reads_only_end_of_big_file(tmp_path, size):
    p = tmp_path / "big.log"
    p.write_bytes(b"x" * size + b"\nletzte Zeile\n")
    assert runner.log_tail(p)[-1] == "letzte Zeile"
    assert runner.log_tail(tmp_path / "fehlt.log") == []
