"""SRBMiner im Katalog: Version, Paket und Algorithmen passen zusammen (Anlass: Mining startete nicht, 14.11.2026).

SRBMiner 3.7.8 behob pearlhash auf NVIDIA 5000 mit Treiber ab 615; 3.7.7 entfernte 'blake3_an'. Werte aus dem
offiziellen GitHub-Release 3.8.8 (md5 aus dem Release gegengeprüft, sha256 selbst gemessen, 14.11.2026).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RIG_DIR = Path(__file__).resolve().parents[1] / "rig"
if str(RIG_DIR) not in sys.path:
    sys.path.insert(0, str(RIG_DIR))

from hydrahive_rig import __version__, catalog  # noqa: E402

SRB = "srbminer"
# In einer SRBMiner-Version entfernte Algorithmen (laut Release-Notizen) → dürfen nicht mehr im Katalog stehen.
REMOVED = {"3.7.7": {"sha3t", "blake3_an", "argon2id_exfer"}}


def _ver(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def test_srbminer_ist_3_8_8_mit_gemessener_pruefsumme():
    m = catalog.miner(SRB)
    assert m["version"] == "3.8.8"
    assert m["sha256"] == "c203e79e9dc467ec5daaa1e1771e08561a70d2c9dcc397364b8ae7ae558e50d8"


def test_url_und_ordner_passen_zur_version():
    m = catalog.miner(SRB)
    dashed = m["version"].replace(".", "-")
    assert m["url"] == (f"https://github.com/doktor83/SRBMiner-Multi/releases/download/{m['version']}/"
                        f"SRBMiner-Multi-{dashed}-Linux.tar.gz")
    assert m["binary"] == f"SRBMiner-Multi-{dashed}/SRBMiner-MULTI"
    assert re.fullmatch(r"[0-9a-f]{64}", m["sha256"])


def test_keine_algorithmen_die_srbminer_entfernt_hat():
    v = _ver(catalog.miner(SRB)["version"])
    gone = set().union(*(algos for since, algos in REMOVED.items() if v >= _ver(since)))
    used = {(c, a) for c, e in catalog.data()["coins"].items() for opts in e["options"].values()
            for m, a in opts if m == SRB}
    assert not [(c, a) for c, a in used if a in gone]


def test_alph_bleibt_ueber_andere_miner_moeglich():
    opts = catalog.data()["coins"]["alph"]["options"]
    assert ["rigel", "alephium"] in opts["nvidia"] and ["lolminer", "ALEPH"] in opts["nvidia"]
    assert ["lolminer", "ALEPH"] in opts["amd"]
    assert all(m != SRB for v in opts.values() for m, _ in v)


def test_prl_auf_nvidia_weiter_mit_srbminer():
    assert [SRB, "pearlhash"] in catalog.data()["coins"]["prl"]["options"]["nvidia"]


def test_neue_client_version_damit_rechner_neu_laden():
    assert _ver(__version__) >= (0, 4, 3)
