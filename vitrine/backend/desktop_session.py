"""Multiseat: Standard-Desktop-Sitzung des Systems für den zweiten Arbeitsplatz ermitteln (lightdm user-session).

Live 24.11.2026: Ohne user-session bot lightdm am zweiten Arbeitsplatz „Default Xsession“ (lightdm-xsession.desktop,
Exec=default) an – der Nutzer landete in einem halben Desktop ohne die System-Einstellungen (XDG_CONFIG_DIRS ohne
xdg-<Distribution>, picom brach ab). Nicht raten, sondern aus dem System lesen:
1. Kandidaten: /usr/share/xsessions/*.desktop, ohne Vitrine-Kiosk, ohne Platzhalter (lightdm-xsession, default,
   Exec=default), ohne NoDisplay=true/Hidden=true. Reine Fenstermanager (openbox, …) nur, wenn sonst nichts da ist.
2. Vorzug: Exec passt zum Ziel von /etc/alternatives/x-session-manager (der vom System gewählte Desktop).
3. Mehrere passen (z. B. Lubuntu und LXQt starten beide startlxqt): die, deren Name eine Distributions-Einstellung
   /etc/xdg/xdg-<Name> hat; sonst die alphabetisch erste – mit Begründung im Ergebnis.
4. Keine eindeutige Wahl → None (lightdm-Standard wie bisher) und Grund im Plan.
Nur lesen; nichts im Home der Nutzer oder im AccountsService ändern.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9._+-]+$")
SKIP = {"hydrahive-vitrine-kiosk", "lightdm-xsession", "default"}
WM_ONLY = {"openbox", "fluxbox", "icewm", "i3", "awesome", "twm", "fvwm", "jwm", "blackbox", "windowmaker", "wmaker",
           "xmonad", "dwm", "herbstluftwm", "bspwm", "openbox-session"}


def _entry(path: Path) -> dict[str, str]:
    """[Desktop Entry] einer .desktop-Datei (nur Schlüssel ohne Sprachzusatz)."""
    out: dict[str, str] = {}
    section = ""
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if line.startswith("["):
            section = line
        elif section == "[Desktop Entry]" and "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            if "[" not in k:
                out.setdefault(k.strip(), v.strip())
    return out


def _exec_target(exec_line: str, root: Path) -> str:
    """Programm aus Exec= (erstes Wort, ohne env-Zuweisungen), aufgelöst unter root, als Pfad relativ zu root."""
    words = [w for w in exec_line.split() if "=" not in w and w != "env"]
    if not words:
        return ""
    prog = words[0]
    if not prog.startswith("/"):
        for d in ("/usr/bin", "/bin", "/usr/local/bin", "/usr/sbin"):
            if (root / d.lstrip("/") / prog).exists():
                prog = f"{d}/{prog}"
                break
        else:
            return prog
    return _resolve(root, prog)


def _resolve(root: Path, path: str) -> str:
    """Symlinks unter root auflösen (auch absolute Ziele wie /etc/alternatives/… → /usr/bin/…), Ergebnis ohne root."""
    cur = path
    for _ in range(16):
        p = root / cur.lstrip("/")
        if not p.is_symlink():
            return cur
        target = os.readlink(p)
        cur = target if target.startswith("/") else os.path.normpath(os.path.join(os.path.dirname(cur), target))
    return cur


def find(root: Path = Path("/")) -> dict:
    """{'name': str | None, 'reason': str, 'candidates': [...]} – reason erklärt die Wahl bzw. warum keine."""
    xs = root / "usr/share/xsessions"
    found: list[tuple[str, dict[str, str]]] = []
    for f in sorted(xs.glob("*.desktop")) if xs.is_dir() else []:
        name = f.name[: -len(".desktop")]
        e = _entry(f)
        if (name in SKIP or not NAME.match(name) or e.get("Exec", "default").strip() in ("", "default")
                or e.get("NoDisplay", "").lower() == "true" or e.get("Hidden", "").lower() == "true"):
            continue
        found.append((name, e))
    desktops = [(n, e) for n, e in found if n.lower() not in WM_ONLY]
    pool = desktops or found
    names = [n for n, _ in pool]
    if not pool:
        return {"name": None, "reason": "no_desktop", "candidates": []}
    xsm = root / "etc/alternatives/x-session-manager"
    target = _resolve(root, "/etc/alternatives/x-session-manager") if xsm.is_symlink() else ""
    matching = [(n, e) for n, e in pool if target and _exec_target(e.get("Exec", ""), root) == target]
    if len(matching) == 1:
        return {"name": matching[0][0], "reason": "x-session-manager", "candidates": names}
    if len(matching) > 1:
        xdg = [n for n, _ in matching if (root / f"etc/xdg/xdg-{n}").is_dir()]
        if len(xdg) == 1:
            return {"name": xdg[0], "reason": "x-session-manager+xdg", "candidates": names}
        return {"name": sorted(n for n, _ in matching)[0], "reason": "x-session-manager+alphabetisch",
                "candidates": names}
    if len(pool) == 1:
        return {"name": pool[0][0], "reason": "only_desktop" if desktops else "only_wm", "candidates": names}
    return {"name": None, "reason": "ambiguous", "candidates": names}
