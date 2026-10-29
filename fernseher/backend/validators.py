"""Adresse des Fernsehers: nur im Heimnetz (SPEC.md „Einstellungen“).

Erlaubt sind private IPv4-Adressen (10/8, 172.16/12, 192.168/16) und Namen ohne öffentliche Endung: einzelne
Namen („bravia“), `.local`, `.lan`, `.home`, `.fritz.box`, `.intra`, `.internal`. So kann das Modul nicht als Tür
nach außen dienen. Loopback, Link-local, Port, Schema und Pfad sind verboten – der Client baut die URL selbst.
"""
from __future__ import annotations

import ipaddress
import re

_LOCAL_SUFFIXES = (".local", ".lan", ".home", ".fritz.box", ".intra", ".internal", ".home.arpa")
_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


class AddressError(ValueError):
    """Adresse liegt nicht im Heimnetz oder ist kein reiner Hostname bzw. IP."""


def normalize_address(raw: str) -> str:
    addr = (raw or "").strip().lower()
    if not addr or len(addr) > 253:
        raise AddressError("leer oder zu lang")
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        ip = None
    if ip is not None:
        if ip.version == 4 and ip.is_private and not (ip.is_loopback or ip.is_link_local or ip.is_unspecified):
            return addr
        raise AddressError("keine private Heimnetz-Adresse")
    labels = addr.split(".")
    if not all(_LABEL.match(part) for part in labels):
        raise AddressError("kein gültiger Name")
    if addr == "localhost":
        raise AddressError("localhost ist nicht erlaubt")
    if len(labels) == 1 or addr.endswith(_LOCAL_SUFFIXES):
        return addr
    raise AddressError("Name zeigt nicht ins Heimnetz")
