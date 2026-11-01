"""Fehlercodes des Moduls Netzwerk (Oberfläche übersetzt über network:err.<code>)."""
from __future__ import annotations

KNOWN: dict[str, str] = {
    "network_not_configured": "Die Dream Machine ist noch nicht eingerichtet.",
    "network_url_invalid": "Die Adresse muss so aussehen: https://192.168.178.1",
    "network_host_not_local": "Nur Geräte im eigenen Heimnetz sind erlaubt.",
    "network_credential_invalid": "Der gewählte Zugang fehlt im Safe.",
    "network_unreachable": "Das Gerät antwortet nicht.",
    "network_auth_failed": "Das Gerät lehnt den Zugang ab – Schlüssel prüfen.",
    "network_cert_unconfirmed": "Das Zertifikat der Dream Machine ist noch nicht bestätigt.",
    "network_cert_changed": "Das Zertifikat der Dream Machine hat sich geändert – bitte neu bestätigen.",
    "network_fingerprint_mismatch": "Der Fingerabdruck stimmt nicht mehr – bitte neu abrufen.",
    "network_bad_response": "Das Gerät hat unerwartet geantwortet.",
    "network_import_invalid": "Diese Datei ist keine Sicherung der Dream Machine.",
    "network_value_invalid": "Dieser Wert ist ungültig.",
}


class NetError(Exception):
    """Fehler mit Code aus KNOWN (wird in den Routen zu coded())."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
