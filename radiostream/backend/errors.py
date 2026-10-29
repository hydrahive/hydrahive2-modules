"""Fehlercodes des Moduls Radiostream mit kurzem Text (Oberfläche übersetzt über radiostream:err.<code>)."""
from __future__ import annotations

KNOWN: dict[str, str] = {
    "radiostream_not_configured": "Noch keine Musikquelle eingetragen.",
    "radiostream_url_invalid": "Die Adresse muss so aussehen: smb://server/freigabe",
    "radiostream_credential_invalid": "Der gewählte Zugang fehlt im Safe oder ist kein Benutzer/Passwort-Zugang.",
    "radiostream_source_unreachable": "Der Server mit der Musik ist nicht erreichbar.",
    "radiostream_auth_failed": "Anmeldung an der Freigabe abgelehnt – Benutzer oder Passwort prüfen.",
    "radiostream_share_not_found": "Diese Freigabe gibt es auf dem Server nicht.",
    "radiostream_scan_running": "Die Bibliothek wird gerade eingelesen.",
    "radiostream_feed_forbidden": "Kein Zugriff.",
    "radiostream_library_empty": "Es gibt noch nichts zu spielen.",
    "radiostream_scan_interrupted": "Das Einlesen wurde unterbrochen (z. B. durch einen Neustart).",
    "radiostream_track_not_found": "Titel nicht gefunden.",
    "radiostream_track_unavailable": "Die Datei ist auf dem Server gerade nicht lesbar.",
    "radiostream_admin_only": "Das dürfen nur Admins.",
}
