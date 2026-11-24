"""Multiseat: Zweiten Arbeitsplatz einschalten – gemeinsamer Weg für Knopf (API) und Installation/Update (§7 N2a, N3).

Ohne FastAPI/HydraHive, damit install.sh es im Vitrine-venv aufrufen kann:
    cd <modul> && <venv>/bin/python -m backend.seat_auto <daten>
Plan-Erzeugung nur hier bzw. in seat_plan (nicht doppelt): Zuordnung aus seats.json gegen den AKTUELLEN Snapshot prüfen
(seats.validate + seat_plan.build_plan), drei Dateien schreiben, multiseat-apply.sh über den einzigen Root-Weg starten
(`sudo -n bash -c "systemd-run … /bin/bash '<skript>' …"`), Ergebnis in <daten>/multiseat/last-run.json.
`auto` in seats.json (N3): Knopf „ausschalten“ setzt false, „einschalten“ true; die Automatik lässt auto:false in Ruhe.
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

from . import seat_plan, seats, seats_snapshot

MODULE_ROOT = Path(__file__).resolve().parents[1]
ETC = Path("/etc/hydrahive2-vitrine")
TIMEOUT = 900                         # apply: apt + Prüfung 90 s; der Rückbau-Timer greift nach 300 s ohnehin


def write_json(path: Path, obj: object) -> None:
    write_text(path, json.dumps(obj, indent=2))


def write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.chmod(0o644)
    tmp.replace(path)


def read_saved(data: Path) -> dict | None:
    try:
        raw = json.loads((data / "seats.json").read_text())
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def set_auto(data: Path, value: bool) -> None:
    """N3: Vermerk, ob Installation/Update den zweiten Arbeitsplatz selbst einschalten darf (nur bei gespeicherter Zuordnung)."""
    saved = read_saved(data)
    if saved and isinstance(saved.get("assignment"), dict):
        write_json(data / "seats.json", {**saved, "auto": value})


def root_cmd(script: Path, *args: Path) -> list[str]:
    """Root-Weg wie install.sh (Kiosk) – systemd-run, damit das Skript außerhalb der Dienst-Sandbox läuft."""
    inner = " ".join(["systemd-run --quiet --wait --pipe --collect /bin/bash", *(shlex.quote(str(p)) for p in (script, *args))])
    return ["sudo", "-n", "bash", "-c", inner]


def write_plan_files(run_dir: Path, plan: dict) -> tuple[Path, Path, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    files = (run_dir / "plan.json", run_dir / "lightdm.conf", run_dir / "xorg.conf")
    write_text(files[0], seat_plan.plan_json(plan))
    write_text(files[1], seat_plan.render_lightdm(plan))
    write_text(files[2], seat_plan.render_xorg(plan))
    return files


def execute(action: str, cmd: list[str], run_dir: Path, *, source: str = "api") -> dict:
    """Root-Aufruf ausführen und das Ergebnis in last-run.json ablegen (gleiches Format für Knopf und Update)."""
    started = int(time.time())
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, check=False)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = -1, "Zeitüberschreitung – der Rückbau-Timer stellt den Stand von vorher wieder her."
    except OSError as e:
        code, out = -1, f"Start fehlgeschlagen: {e}"
    res = {"action": action, "source": source, "started": started, "finished": int(time.time()), "exit": code,
           "ok": code == 0, "lines": out.splitlines()[-40:]}
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "last-run.json", res)
    return res


def auto_apply(data: Path, *, sys_root: Path = Path("/"), etc: Path | None = None,
               module_root: Path | None = None) -> str:
    """§7 N2a: beim Installieren/Update einschalten, wenn alles passt. Gibt den Grund zurück (für Meldung und Tests)."""
    etc = etc or ETC
    snap = seats_snapshot.read(sys_root)
    if not seats.monitor_detected(snap):
        return "no_monitor"
    if (etc / "multiseat.aktiv").is_file():
        return "already_on"
    saved = read_saved(data)
    if not saved or not isinstance(saved.get("assignment"), dict):
        return "not_saved"
    if saved.get("auto") is False:
        return "auto_off"
    try:
        plan = seat_plan.build_plan(snap, seats.validate(snap, saved["assignment"]))
    except seats.SeatError as e:
        return f"invalid:{e.code}"
    files = write_plan_files(data / "multiseat", plan)
    script = (module_root or MODULE_ROOT) / "extension" / "multiseat-apply.sh"
    res = execute("apply", root_cmd(script, *files), data / "multiseat", source="update")
    return "applied" if res["ok"] else f"apply_failed:{res['exit']}"


MESSAGES = {
    "no_monitor": "",
    "already_on": "Vitrine-Multiseat: zweiter Arbeitsplatz ist schon eingeschaltet – nichts zu tun.",
    "not_saved": "Vitrine-Multiseat: zweiter Bildschirm erkannt, aber noch keine Zuordnung gespeichert. Der Bildschirm "
                 "bleibt an; in der Vitrine unter „Arbeitsplätze“ zuordnen und „Übernehmen“ klicken.",
    "auto_off": "Vitrine-Multiseat: zweiter Arbeitsplatz wurde bewusst ausgeschaltet und bleibt aus. Einschalten in der "
                "Vitrine unter „Arbeitsplätze“.",
    "invalid": "Vitrine-Multiseat: gespeicherte Zuordnung passt nicht zu den Geräten von jetzt ({}). In der Vitrine "
               "unter „Arbeitsplätze“ neu zuordnen und „Übernehmen“ klicken.",
    "applied": "Vitrine-Multiseat: zweiter Arbeitsplatz automatisch eingeschaltet.",
    "apply_failed": "Vitrine-Multiseat: automatisches Einschalten hat nicht geklappt (Exit {}); der Stand von vorher ist "
                    "wiederhergestellt. Details in der Vitrine unter „Arbeitsplätze“.",
}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Aufruf: python -m backend.seat_auto <datenordner>", file=sys.stderr)
        return 2
    try:
        reason = auto_apply(Path(argv[1]))
    except Exception as e:                   # Installation/Update darf daran nie scheitern
        print(f"Vitrine-Multiseat: Automatik übersprungen ({e.__class__.__name__}: {e})", file=sys.stderr)
        return 0
    key, _, detail = reason.partition(":")
    msg = MESSAGES.get(key, reason)
    if msg:
        print(msg.format(detail))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
