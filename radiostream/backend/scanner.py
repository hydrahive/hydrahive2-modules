"""Bibliothek einlesen (SPEC „Bauplan Etappe 1 – Einlesen“).

1. Ordner per SMB durchgehen, je Audiodatei Größe + Änderungszeit mit der DB vergleichen.
2. Nur Neues/Geändertes öffnen und Kopfdaten lesen – EIN Strang (Till 26.10.: „gemütlich reicht“).
3. In Paketen speichern (Abbruch → nächster Lauf setzt fort, weil Gespeichertes unverändert ist).
4. Nur bei vollständigem Durchgang: Nicht-mehr-Gesehenes als `missing` markieren (nie löschen).
Läuft im Hintergrund-Thread (start_in_background), nie in der Ereignisschleife. Nur lesen.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from . import library, scan_state, settings_store, tags
from .smb_source import SourceError, open_source

logger = logging.getLogger(__name__)
WORKERS = 1
BATCH = 500


@dataclass
class ScanResult:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    missing: int = 0
    errors: int = 0
    cancelled: bool = False


def _read_tags(conn, rel: str) -> dict:
    with conn.open(rel) as fh:
        return tags.read(fh, rel)


def _flush(source_id: str, batch: list, errors: list, res: ScanResult, known: dict) -> None:
    library.upsert_batch(source_id, batch)
    library.add_errors(source_id, errors)
    for rel, *_ in batch:
        if rel in known:
            res.updated += 1
        else:
            res.added += 1
    scan_state.add(added=sum(1 for r, *_ in batch if r not in known),
                   updated=sum(1 for r, *_ in batch if r in known), errors=len(errors))
    res.errors += len(errors)
    batch.clear()
    errors.clear()


def _process(conn, source_id: str, known: dict, seen: set, res: ScanResult) -> bool:
    """Durchgang; True = vollständig, False = abgebrochen."""
    batch: list = []
    errors: list = []
    for rel_dir, files in conn.walk():
        if scan_state.cancelled():
            _flush(source_id, batch, errors, res, known)
            return False
        scan_state.add(dirs_seen=1)
        todo = []
        for name, size, mtime in files:
            if not tags.is_audio(name):
                continue
            rel = f"{rel_dir}/{name}" if rel_dir else name
            seen.add(rel)
            scan_state.add(files_seen=1)
            old = known.get(rel)
            if old and old[0] == size and old[1] == mtime:
                if old[2] == "missing":
                    library.set_state(source_id, [rel], "ok")
                res.unchanged += 1
                scan_state.add(unchanged=1)
                continue
            todo.append((rel, size, mtime))
        scan_state.add(todo=len(todo))
        for rel, size, mtime in todo:
            if scan_state.cancelled():
                _flush(source_id, batch, errors, res, known)
                return False
            try:
                batch.append((rel, size, mtime, _read_tags(conn, rel)))
            except tags.TagError:
                errors.append((rel, "unreadable_tags"))
            except OSError:
                errors.append((rel, "read_failed"))
            scan_state.add(done=1)
            if len(batch) + len(errors) >= BATCH:
                _flush(source_id, batch, errors, res, known)
    _flush(source_id, batch, errors, res, known)
    return True


def run_scan() -> ScanResult:
    """Ein Durchgang (blockierend). SourceError bei fehlender/unerreichbarer Quelle."""
    src = settings_store.get()
    if not src:
        raise SourceError("radiostream_not_configured")
    began = scan_state.try_begin()
    settings_store.mark("scanning", started=True)
    res = ScanResult()
    try:
        conn = open_source(src["url"], src["owner"], src["credential_name"])
    except SourceError as exc:
        settings_store.mark("error", error=exc.code)
        if began:
            scan_state.finish(exc.code)
        raise
    try:
        source_id = src["source_id"]
        known = library.known(source_id)
        seen: set[str] = set()
        complete = _process(conn, source_id, known, seen, res) and not scan_state.cancelled()
        if complete:
            gone = [rel for rel, (_, _, st) in known.items() if rel not in seen and st != "missing"]
            res.missing = library.set_state(source_id, gone, "missing")
            scan_state.add(missing=res.missing)
        res.cancelled = not complete
        settings_store.mark("idle", finished=True)
        logger.info("Radiostream: Einlesen %s – neu %d, geändert %d, fehlend %d, Fehler %d",
                    "abgebrochen" if res.cancelled else "fertig", res.added, res.updated, res.missing, res.errors)
        return res
    finally:
        conn.close()
        if began:
            scan_state.finish()


def start_in_background() -> None:
    def _run():
        try:
            run_scan()
        except SourceError as exc:
            logger.info("Radiostream: Einlesen nicht möglich: %s", exc.code)
        except Exception:  # noqa: BLE001 – Hintergrund darf nie still sterben
            logger.exception("Radiostream: Einlesen abgebrochen")
    threading.Thread(target=_run, name="radiostream-scan", daemon=True).start()
