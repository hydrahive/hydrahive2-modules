"""Entrümpeln, Teil 1: Abschaltlisten von cleanyourtv lesen und mit den Paketen eines Fernsehers abgleichen. Nur lesend.

Quelle sind die getesteten Listen `examples/*/debloat*.txt` am festen Stand (backend/source.py). Ein Paket gilt als
„empfohlen“, wenn die passende Liste des Geräts es abschaltet; dazu steht, wie viele aller Listen das tun (Logik wie
cleanyourtv tools/match.py). Geschützt ist Android selbst (CORE_RE wie tools/recovery.py), was eine Liste ausdrücklich
anlassen will, und was die Werkstatt selbst braucht (Startbildschirm, Original, Einrichtungs-Helfer – dafür ist das
Aufspielen zuständig). Entschieden wird nach dem, was das Gerät meldet: Marke, Build, Produkt.
"""
from __future__ import annotations

import re
from collections import Counter

from . import guard, install

_PKG = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+")
# Wie cleanyourtv tools/recovery.py (b953804): ohne diese startet Android womöglich nicht mehr (#884, #1578, #2803).
CORE_RE = re.compile(
    r"^(android|android\.ext\.(services|shared)|com\.android\.sdksandbox|com\.android\.location\.fused|"
    r"com\.android\.systemui|com\.android\.shell|com\.android\.phone|com\.android\.settings|com\.android\.tv\.settings|"
    r"com\.(google\.)?android\.(permissioncontroller|packageinstaller|ext\.services|ext\.shared|modulemetadata)|"
    r"com\.google\.android\.overlay\.modules.*|com\.android\.providers\..*|com\.cltv\.mal|"
    r"com\.mediatek\.(tis|tv\.service|tv\.agent))$")
CORE_OK = re.compile(r"^com\.android\.providers\.(calendar|contacts|userdictionary|blockednumber)$")
# Gewicht je Merkmal, das im Kopf einer Liste vorkommt (Build zählt am meisten: gleiche Firmware, gleiche Pakete).
_WEIGHTS = (("build_id", 30), ("incremental", 15), ("product", 15), ("device", 10), ("model", 5))
MIN_SCORE = 40                                     # darunter keine Geräteliste, nur die Zählung über alle


def is_core(pkg: str) -> bool:
    return bool(CORE_RE.match(pkg)) and not CORE_OK.match(pkg)


def read_list(text: str) -> tuple[list[tuple[str, str, str]], set[str], str]:
    """([(paket, notiz, gruppe)] abgeschaltet, {ausdrücklich angelassen}, Kopf) einer Liste.

    Kopf = Kommentare vor dem ersten Paket. Gruppe = erste Zeile des letzten Kommentarblocks vor dem Paket.
    Angelassen: `# paket` allein auf einer Zeile (wie match.py) und die Pakete im Kopf-Absatz „Left enabled on purpose“.
    """
    off: list[tuple[str, str, str]] = []
    kept: set[str] = set()
    head: list[str] = []
    group, block, after_blank = "", "", True
    for raw in text.replace("\r", "").splitlines():
        line = raw.strip()
        if not line or line == "#":
            after_blank = True
            if not off:
                head.append("")
            continue
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            words = body.partition("#")[0].split()
            if off and len(words) == 1 and _PKG.fullmatch(words[0]):
                kept.add(words[0])
            else:
                if not off:
                    head.append(body)
                if after_blank:
                    block = body[:80]
            after_blank = False
            continue
        words = line.partition("#")[0].split()
        if words and _PKG.fullmatch(words[0]):
            group = block
            off.append((words[0], line.partition("#")[2].strip()[:160], group))
        after_blank = False
    names = {p for p, _, _ in off}
    return off, (kept | _left_enabled(head)) - names, "\n".join(head)


def _left_enabled(head: list[str]) -> set[str]:
    """Pakete im Absatz „Left enabled on purpose:“ des Kopfes (bis zur nächsten Leerzeile)."""
    out: set[str] = set()
    inside = False
    for line in head:
        if "Left enabled on purpose:" in line:
            inside, line = True, line.split("Left enabled on purpose:", 1)[1]
        elif not line:
            inside = False
        if inside:
            out |= {m.group(0) for m in _PKG.finditer(line) if m.group(0).count(".") >= 2}
    return out


def _has(text: str, word: str) -> bool:
    return bool(word) and re.search(r"(?<![A-Za-z0-9_])" + re.escape(word) + r"(?![A-Za-z0-9_])", text) is not None


def score(head: str, brand_of_list: str, ident: dict[str, str]) -> int:
    """Wie gut eine Liste zum Gerät passt. Andere Marke → 0."""
    if not brand_of_list or brand_of_list.lower() != ident.get("brand", "").lower():
        return 0
    return sum(w for key, w in _WEIGHTS if _has(head, ident.get(key, "")))


def peers(lists: dict[str, dict], ident: dict[str, str]) -> tuple[list[str], int]:
    """Alle Listen mit der höchsten Übereinstimmung (gleiche Firmware → meist mehrere Geräte) und deren Punkte."""
    scored = {k: score(v["head"], v["brand"], ident) for k, v in lists.items()}
    top = max(scored.values(), default=0)
    if top < MIN_SCORE:
        return [], top
    return sorted(k for k, s in scored.items() if s == top), top


# Feste deutsche Gruppen statt der freien englischen Überschriften der Listen (Stichworte in Überschrift + Notiz).
GROUPS = (("tracking", ("track", "telemetr", "analytic", "acr", "samba", "feedback", "diagnos", "log ", "log capture",
                        "bugreport", "privacy", "adservices", "personali", "federated", "remote support", "agent")),
          ("ads", ("promo", "ads", "advert", "content", "recommend", "push", "select", "discover", "channel",
                   "waterfall", "autoinstall", "partner")),
          ("demo", ("demo", "retail", "store", "hotel", "b2b", "exhibit", "sticker", "professional")),
          ("home", ("launcher", "home", "setup wizard", "setupwraith", "screensaver")),
          ("help", ("help", "manual", "guide", "instruction", "tips", "repair", "support")))


def group_of(*texts: str) -> str:
    """Erster Text mit Treffer zählt (Notiz und Paketname vor der Überschrift der Liste: sie sagen mehr übers Paket)."""
    for text in texts:
        t = f" {text.lower()} "
        g = next((g for g, words in GROUPS if any(w in t for w in words)), "")
        if g:
            return g
    return "other"


def protected(pkg: str, stock: str) -> str:
    """Grund, warum ein Schalter gesperrt ist, sonst leer."""
    if is_core(pkg):
        return "core"
    if pkg in (install.OUR, stock, guard.SETUP):
        return "home"
    return ""


def _common(c: Counter) -> str:
    return c.most_common(1)[0][0] if c else ""


def evaluate(packages: dict[str, str], lists: dict[str, dict], ident: dict[str, str], stock: str) -> dict:
    """Pakete des Geräts ({paket: 'on'|'off'}) gegen die Listen.

    Empfohlen ist, was die Mehrheit der passenden Listen abschaltet – nicht eine einzelne Liste, sonst kämen die
    Vorlieben eines Besitzers mit (TCL AU02: eine Liste schaltet Netflix ab, die Mehrheit nicht). Lässt auch nur eine
    passende Liste es bewusst an, gilt es als umstritten und wird nicht empfohlen (TCL AU02: com.tcl.ttvs ist dort
    auch der Firmware-Updater). Gezeigt wird, was empfohlen, schon aus oder in einer
    passenden Liste genannt ist.
    """
    names, pts = peers(lists, ident)
    off_n, kept_n, notes, heads, all_n = Counter(), Counter(), {}, {}, Counter()
    for k, v in lists.items():
        mine = k in names
        for p, note, group in v["off"]:
            if p not in packages:
                continue
            all_n[p] += 1
            if mine:
                off_n[p] += 1
                notes.setdefault(p, Counter())[note] += bool(note) or 0
                heads.setdefault(p, Counter())[group] += 1
        if mine:
            kept_n.update(p for p in v["kept"] if p in packages)
    rows = []
    for p, st in sorted(packages.items()):
        rec = bool(names) and off_n[p] * 2 > len(names) and not kept_n[p]     # umstritten → nicht empfohlen
        if not rec and st == "on" and not off_n[p]:
            continue
        note = _common(Counter({n: c for n, c in notes.get(p, Counter()).items() if n}))
        rows.append({"package": p, "state": st, "recommended": rec, "of": off_n[p], "kept": kept_n[p],
                     "lists": all_n[p], "note": note, "group": group_of(f"{note} {p}", _common(heads.get(p, Counter()))),
                     "locked": protected(p, stock)})
    order = [g for g, _ in GROUPS] + ["other"]
    rows.sort(key=lambda r: (not r["recommended"], order.index(r["group"]), -r["of"], r["package"]))
    return {"lists_used": names, "score": pts, "total_lists": len(lists), "packages": rows,
            "off_count": sum(r["state"] == "off" for r in rows),
            "recommended_on": sum(r["recommended"] and r["state"] == "on" and not r["locked"] for r in rows)}
