"""Geteilte Eingabe-Validierung für das Home-Assistant-Modul.

Diese Werte fließen in HA-REST-URLs/Bodies (entity_id → /states/<id>, domain +
service → /services/<domain>/<service>). Zentral validiert — eine Quelle für
Routen UND Agent-Tools. Kein Pfad-/Param-Schmuggel in die Upstream-API.

HA-Konventionen:
  entity_id : "<domain>.<object_id>"  (z.B. light.wohnzimmer, sensor.temp_bad)
  domain    : Kleinbuchstaben + Ziffern + _   (z.B. light, switch, climate)
  service   : Kleinbuchstaben + Ziffern + _   (z.B. turn_on, set_temperature)
"""
from __future__ import annotations

import re

# domain.object_id — beide Teile [a-z0-9_], getrennt durch genau einen Punkt.
ENTITY_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
DOMAIN_RE = re.compile(r"^[a-z0-9_]+$")
SERVICE_RE = re.compile(r"^[a-z0-9_]+$")


def is_entity(value: str) -> bool:
    return bool(ENTITY_RE.match(value or ""))


def is_domain(value: str) -> bool:
    return bool(DOMAIN_RE.match(value or ""))


def is_service(value: str) -> bool:
    return bool(SERVICE_RE.match(value or ""))


def domain_of(entity_id: str) -> str:
    """Domain-Teil einer entity_id, oder '' wenn ungültig."""
    return entity_id.split(".", 1)[0] if is_entity(entity_id) else ""
