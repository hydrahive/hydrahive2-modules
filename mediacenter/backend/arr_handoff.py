"""Uebergibt einen Suchtreffer an Radarr/Sonarr.

Die Suche bleibt im Mediacenter, den Download macht der Zieldienst — der kennt
Bibliothek, Qualitaetsprofile, Umbenennung und Import.

Damit loest sich auch das Kategorie-Problem: ein Direktdownload des
Mediacenters landet in einer SABnzbd-Kategorie, die Radarr ueberwacht, ohne
dass Radarr ihn bestellt hat (-> importBlocked). Uebergibt Radarr selbst,
kennt es den Download und importiert ihn korrekt.

Kette: lookup -> ggf. anlegen -> POST /release {guid, indexerId}

Alle schreibenden Aufrufe laufen ueber eine ausdrueckliche Nutzeraktion. Es gibt
bewusst KEIN Agent-Tool dafuer (SPEC-V3.md, E5 folgt mit Bestaetigungsgate).
"""
from __future__ import annotations

from dataclasses import dataclass

from . import arr_client as client
from .arr_credentials import ARR_SERVICES, resolve_arr_connection
from .errors import MediacenterConfigError
from .models import MediaType, ProfileDecision

# Welcher Dienst ist fuer welchen Medientyp zustaendig? Buecher, Hoerbuecher und
# Musik kennen Radarr/Sonarr nicht — die bleiben beim Direktweg an SABnzbd.
_SERVICE_BY_MEDIA: dict[str, str] = {"movie": "radarr", "tv": "sonarr"}


@dataclass(frozen=True)
class HandoffResult:
    service: str
    title: str
    added: bool      # wurde der Titel neu in der Bibliothek angelegt?
    pushed: bool     # wurde das Release zum Download uebergeben?


def service_for(media_type: MediaType | str) -> str | None:
    """Zustaendiger Dienst oder None, wenn keiner passt."""
    return _SERVICE_BY_MEDIA.get(str(media_type))


def _identifier(decision: ProfileDecision, service: str) -> tuple[str | None, str | None]:
    """(imdb_id, tvdb_id) fuer den Lookup."""
    meta = decision.release.meta
    if meta is None:
        return None, None
    if service == "sonarr":
        return (meta.imdb_id, meta.tvdb_id)
    return (meta.imdb_id, None)


def _add_payload(service: str, found: dict, *, quality_profile_id: int,
                 root_folder_path: str) -> dict:
    """Baut die Anlage-Nutzlast. Nur Felder, die der Dienst wirklich braucht."""
    payload = {
        "title": found.get("title"),
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": True,
    }
    if service == "radarr":
        payload["tmdbId"] = found.get("tmdbId")
        payload["titleSlug"] = found.get("titleSlug")
        payload["year"] = found.get("year")
        # Suche nach dem Anlegen NICHT automatisch starten — das Release
        # uebergeben wir gleich selbst und wollen keinen zweiten Download.
        payload["addOptions"] = {"searchForMovie": False}
    else:
        payload["tvdbId"] = found.get("tvdbId")
        payload["titleSlug"] = found.get("titleSlug")
        payload["seasonFolder"] = True
        payload["addOptions"] = {"searchForMissingEpisodes": False}
    return payload


async def handoff(
    username: str,
    decision: ProfileDecision,
    service: str,
    *,
    quality_profile_id: int | None = None,
    root_folder_path: str | None = None,
) -> HandoffResult:
    """Uebergibt einen Treffer an Radarr/Sonarr.

    Raises:
        ValueError: unbekannter Dienstname (kein frei waehlbares Ziel).
        MediacenterConfigError: fachliche Ablehnung mit stabilem Fehlercode.
    """
    if service not in ARR_SERVICES:
        raise ValueError(f"Unbekannter Dienst: {service!r}")
    if decision.decision != "eligible":
        raise MediacenterConfigError("result_not_eligible")
    if service_for(decision.media_type) != service:
        raise MediacenterConfigError("arr_service_mismatch")

    imdb_id, tvdb_id = _identifier(decision, service)
    if not imdb_id and not tvdb_id:
        # Ohne Identifikator koennte der Dienst den falschen Titel treffen.
        raise MediacenterConfigError("arr_identifier_missing")

    connection = resolve_arr_connection(username, service)
    found = await client.lookup(connection, imdb_id=imdb_id, tvdb_id=tvdb_id)
    if not found:
        raise MediacenterConfigError("arr_title_not_found")

    added = False
    if not found.get("id"):
        if not quality_profile_id or not root_folder_path:
            # Kein Raten: Profil und Ordner waehlt der Nutzer.
            raise MediacenterConfigError("arr_target_required")
        await client.add_title(connection, _add_payload(
            service, found, quality_profile_id=quality_profile_id,
            root_folder_path=root_folder_path))
        added = True

    indexer_id = await client.default_indexer_id(connection)
    if not indexer_id:
        raise MediacenterConfigError("arr_indexer_missing")
    pushed = await client.push_release(connection, decision.release.guid, indexer_id)

    return HandoffResult(
        service=service, title=str(found.get("title") or decision.release.title),
        added=added, pushed=bool(pushed),
    )
