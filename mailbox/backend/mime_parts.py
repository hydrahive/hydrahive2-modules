"""Anhänge einer Rohmail in fester Reihenfolge – gemeinsam für Webmail-Download und Agenten-Werkzeug,
damit „Anhang Nr. 2“ überall dasselbe ist. Reihenfolge = Reihenfolge der Teile in der Mail."""
from __future__ import annotations

import email
import email.policy
import re


def parts(raw: bytes) -> list:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    out = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        disp = (part.get_content_disposition() or "").lower()
        cid = (part.get("Content-ID") or "").strip()
        if part.get_filename() or disp == "attachment" or (cid and not part.get_content_type().startswith("text/")):
            out.append(part)
    return out


def safe_name(name: str) -> str:
    """Dateiname ohne Steuerzeichen, Pfadtrenner oder Anführungszeichen; nie leer, höchstens 200 Zeichen."""
    cleaned = re.sub(r"[\x00-\x1f\x7f\"\\/]+", "_", name or "").strip(" .")
    return (cleaned or "anhang")[:200]
