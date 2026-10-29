"""Hörer-Seite anwenden (PLAN-E2.md Punkt 5): Dateien schreiben, nginx-Block prüfen und laden – oder entfernen.

Der root-Befehl enthält nur feste Pfade. Der Block wird aus einer Datei im Moduldatenordner kopiert (nie als Text im
Befehl). Vor dem Prüfen wird die bisherige Fassung gesichert; lehnt `nginx -t` ab, kommt sie zurück und nginx wird
mit der alten Fassung neu geladen.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from . import listener_site

SITE = "hydrahive-radiostream"
AVAILABLE = f"/etc/nginx/sites-available/{SITE}"
ENABLED = f"/etc/nginx/sites-enabled/{SITE}"


def apply(st: dict, *, root: Callable[[str], tuple[int, str]], data_dir: Path, web_dir: Path,
          write: Callable[[Path, str], None]) -> bool:
    for name, text in listener_site.page_files(st).items():
        write(web_dir / name, text)
    conf = data_dir / "nginx.conf"
    write(conf, listener_site.nginx_conf(st, web_dir=str(web_dir)))
    rc, _ = root(
        f"if [ -e {AVAILABLE} ]; then cp -a {AVAILABLE} {AVAILABLE}.alt; else rm -f {AVAILABLE}.alt; fi\n"
        f"install -m 644 {conf} {AVAILABLE} && ln -sf {AVAILABLE} {ENABLED}\n"
        f"if nginx -t >/dev/null 2>&1; then rm -f {AVAILABLE}.alt; systemctl reload nginx; exit 0; fi\n"
        f"if [ -e {AVAILABLE}.alt ]; then mv -f {AVAILABLE}.alt {AVAILABLE}; else rm -f {ENABLED} {AVAILABLE}; fi\n"
        f"nginx -t >/dev/null 2>&1 && systemctl reload nginx\nexit 1")
    return rc == 0


def remove(root: Callable[[str], tuple[int, str]], data_dir: Path) -> None:
    (data_dir / "nginx.conf").unlink(missing_ok=True)
    root(f"if [ -e {ENABLED} ] || [ -e {AVAILABLE} ]; then rm -f {ENABLED} {AVAILABLE}\n"
         f"nginx -t >/dev/null 2>&1 && systemctl reload nginx; fi; exit 0")


def port_taken_by_other(port: int, root: Callable[[str], tuple[int, str]]) -> bool:
    """Belegt jemand außer nginx den Port? (nginx selbst = unsere eigene Hörer-Seite.)

    Über root: Als HydraHive-Nutzer zeigt `ss` die Namen fremder Prozesse nicht (hydratest 29.10.) – dann sähe auch
    die eigene nginx-Seite „fremd“ aus. Der Port ist eine geprüfte Zahl (station.LIMITS)."""
    rc, out = root(f"ss -Hltnp 'sport = :{int(port)}'")
    if rc != 0:
        return False
    return any(line.strip() and '"nginx"' not in line for line in out.splitlines())
