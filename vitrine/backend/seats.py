"""Multiseat M1: Zuordnungs-Vorschlag Vitrine (seat0) / Zweiter Arbeitsplatz (seat1) (ziele/vitrine-multiseat.md §2).

`suggest(snapshot)` ist eine reine Funktion über den Snapshot aus seats_snapshot.read() – testbar mit nachgestellten
Daten. Regeln:
- seat0 (Vitrine): das USB-Display (EVDI) und eine ANDERE echte Grafikkarte als Haupt-GPU (M0: Xorg braucht sie per
  BusID), bevorzugt eine ohne verbundenen Bildschirm.
- seat1 (Zweiter Arbeitsplatz): die echte Grafikkarte mit verbundenem Bildschirm, ihr Ton (gleiche PCI-Karte) und die
  Eingabegeräte, die nicht am USB-Zweig der Vitrine-Eingabe hängen.
- Vitrine-Eingabe = was die Vitrine schon kennt (über ihr Bluetooth gekoppelt). Sonst wird NICHT geraten: Feld leer,
  die Oberfläche fragt.
- Nicht machbar (kein Angebot): kein EVDI, keine zweite echte Grafikkarte, kein verbundener Bildschirm.
Hier wird nichts umgeschaltet; die Zuordnung wird erst in M2 angewendet.
"""
from __future__ import annotations

SEATS = ("seat0", "seat1")


def _monitor(g: dict) -> bool:
    return any(o.get("connected") for o in g.get("outputs", []))


def _same_card(pci_a: str | None, pci_b: str | None) -> bool:
    """Gleiche PCI-Karte = gleiche Domäne, Bus und Gerät; nur die Funktion (.0 Grafik, .1 HDMI-Ton) unterscheidet."""
    return bool(pci_a and pci_b) and pci_a.rsplit(".", 1)[0] == pci_b.rsplit(".", 1)[0]


def _one(items: list[dict]) -> dict | None:
    return items[0] if len(items) == 1 else None


def monitor_detected(snapshot: dict) -> bool:
    """Echter Bildschirm an einer Nicht-EVDI-Karte – der Fall, in dem install.sh heute den Kiosk still auslässt."""
    return any(not g["evdi"] and _monitor(g) for g in snapshot.get("gpus", []))


def suggest(snapshot: dict) -> dict:
    gpus = snapshot.get("gpus", [])
    evdi = [g for g in gpus if g["evdi"]]
    real = [g for g in gpus if not g["evdi"]]
    with_mon = [g for g in real if _monitor(g)]
    reasons: list[str] = []
    if not evdi:
        reasons.append("no_evdi")
    if len(real) < 2:
        reasons.append("one_gpu")
    if not with_mon:
        reasons.append("no_monitor")

    seat1_gpu = _one(with_mon)
    if with_mon and seat1_gpu is None:
        reasons.append("gpu_unclear")                         # mehrere Karten mit Bildschirm → Admin wählt
    others = [g for g in real if g is not seat1_gpu]
    without = [g for g in others if not _monitor(g)]
    seat0_gpu = _one(without) or (_one(others) if seat1_gpu else None)
    if seat1_gpu and seat0_gpu is None and len(real) >= 2:
        reasons.append("gpu_unclear")
    feasible = not reasons

    seat: dict[str, str | None] = {}
    for g in evdi:
        seat[g["id"]] = "seat0"
    for g in real:
        seat[g["id"]] = "seat1" if g is seat1_gpu else "seat0" if g is seat0_gpu else None
    for s in snapshot.get("sound", []):
        if seat1_gpu and _same_card(s["pci"], seat1_gpu["pci"]):
            seat[s["id"]] = "seat1"
        elif seat0_gpu and _same_card(s["pci"], seat0_gpu["pci"]):
            seat[s["id"]] = "seat0"
        else:
            seat[s["id"]] = "seat0"                             # nicht zugeordnet bleibt beim ersten Arbeitsplatz

    vitrine_bt = set(snapshot.get("vitrine_bt", []))
    known = [i for i in snapshot.get("inputs", []) if i.get("bt") and i["bt"] in vitrine_bt]
    branches = {i["branch"] for i in known if i.get("branch")}
    unclear_input = False
    for i in snapshot.get("inputs", []):
        if i in known:
            seat[i["id"]] = "seat0"
        elif not known or not i.get("branch"):
            seat[i["id"]] = None                                # nicht raten: Admin ordnet zu
            unclear_input = True
        else:
            seat[i["id"]] = "seat0" if i["branch"] in branches else "seat1"

    return {"feasible": feasible, "reasons": reasons, "monitor_detected": monitor_detected(snapshot),
            "inputs_unclear": unclear_input, "assignment": seat if feasible else {}}


def device_ids(snapshot: dict) -> set[str]:
    return {d["id"] for key in ("gpus", "sound", "inputs") for d in snapshot.get(key, [])}


class SeatError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def validate(snapshot: dict, assignment: object) -> dict[str, str]:
    """Vom Admin bestätigte Zuordnung prüfen: nur Geräte aus dem aktuellen Snapshot, nur seat0/seat1, Grafik passt."""
    if not isinstance(assignment, dict) or not assignment:
        raise SeatError("vitrine_seat_empty")
    ids = device_ids(snapshot)
    out: dict[str, str] = {}
    for dev, s in assignment.items():
        if not isinstance(dev, str) or dev not in ids:
            raise SeatError("vitrine_seat_unknown_device")
        if s not in SEATS:
            raise SeatError("vitrine_seat_bad_seat")
        out[dev] = s
    gpus = {g["id"]: g for g in snapshot.get("gpus", [])}
    if any(out.get(g) != "seat0" for g, x in gpus.items() if x["evdi"]):
        raise SeatError("vitrine_seat_evdi_not_seat0")
    real = {s: [g for g, x in gpus.items() if not x["evdi"] and out.get(g) == s] for s in SEATS}
    if len(real["seat0"]) != 1 or len(real["seat1"]) != 1:
        raise SeatError("vitrine_seat_gpu_per_seat")          # je Arbeitsplatz genau eine echte Grafikkarte (M0)
    return out
