from __future__ import annotations

import os

# --- Externe Adressen -------------------------------------------------------
#
# Alle Adressen kommen aus Umgebungsvariablen. Die Defaults entsprechen dem
# bisherigen Verhalten, damit bestehende Installationen unveraendert laufen.
# KEINE Adresse darf sonst irgendwo im Code stehen — ein Umzug soll eine
# Konfigurationsaenderung sein, kein Code-Eingriff (Tests wachen darueber).


def _origin(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip().rstrip("/")


def _host_of(origin: str) -> str:
    """Hostname aus einem Origin — ohne Schema, Port und Pfad."""
    without_scheme = origin.split("://", 1)[-1]
    return without_scheme.split("/", 1)[0].split(":", 1)[0].lower()


def _host_set(name: str, default: str) -> frozenset[str]:
    raw = os.environ.get(name, default)
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


# Newznab-Indexer
INDEXER_ORIGIN = _origin("HH_MEDIACENTER_INDEXER_ORIGIN", "https://treasure-maps.com")
INDEXER_API_URL = f"{INDEXER_ORIGIN}/api"
INDEXER_HOST = _host_of(INDEXER_ORIGIN)
# NZB-Downloads laufen bei vielen Indexern ueber einen eigenen Dateihost.
# Default: "file.<indexer-host>" — zieht bei einem Wechsel automatisch mit.
INDEXER_FILE_HOST = os.environ.get(
    "HH_MEDIACENTER_INDEXER_FILE_HOST", f"file.{INDEXER_HOST}"
).strip().lower()
INDEXER_CREDENTIAL = "tresuere_token"

# Bildhosts fuer Cover/Backdrops (Allowlist, kommagetrennt)
COVER_HOSTS = _host_set(
    "HH_MEDIACENTER_COVER_HOSTS",
    f"picbit.io,cdn.{INDEXER_HOST},{INDEXER_HOST}",
)

# Radarr/Sonarr — leer bedeutet: nicht konfiguriert, Funktion deaktiviert.
# Bewusst KEIN Default auf eine fremde Adresse.
RADARR_ORIGIN = _origin("HH_MEDIACENTER_RADARR_ORIGIN")
SONARR_ORIGIN = _origin("HH_MEDIACENTER_SONARR_ORIGIN")
RADARR_CREDENTIAL = "radarr_token"
SONARR_CREDENTIAL = "sonarr_token"

MAX_CREDENTIAL_LENGTH = 4096
MAX_QUERY_LENGTH = 200
MAX_RESULTS = 100
MAX_XML_BYTES = 4 * 1024 * 1024
MAX_TITLE_LENGTH = 512
INDEXER_TIMEOUT_SECONDS = 15.0
RESULT_TTL_SECONDS = 15 * 60
SAB_CREDENTIAL = "sabnzb_token"
# Adresse aus der Umgebung; ohne Angabe wird sie aus dem `url_pattern` des
# hinterlegten Credentials uebernommen (siehe sab_credentials.py).
#
# Vorher stand hier eine konkrete IP als Default — falsch fuer jede andere
# Installation. Sie einfach zu entfernen haette den laufenden Betrieb
# abgeschaltet (die Variable ist nirgends gesetzt), deshalb dient jetzt das
# Credential selbst als Quelle: der Nutzer pflegt die Adresse dort ohnehin.
SAB_ALLOWED_ORIGIN = _origin("HH_MEDIACENTER_SAB_ORIGIN")
SAB_TIMEOUT_SECONDS = 15.0
SAB_MAX_JSON_BYTES = 1024 * 1024
MAX_NZB_BYTES = 16 * 1024 * 1024

SAB_CATEGORIES: dict[str, str] = {
    "movie": "movies",
    "tv": "tv",
    "book": "ebook",
    "audiobook": "audiobook",
    "audioplay": "audiobook",
    "music": "audio",
}

NEWZNAB_CATEGORIES: dict[str, tuple[int, ...]] = {
    "movie": (2140, 2145, 2150),
    "tv": (5140, 5145),
    "book": (7120,),
    "audiobook": (3130,),
    "audioplay": (3130,),
    "music": (3010, 3040),
}

NEWZNAB_CAPABILITY_TYPES: dict[str, str] = {
    "movie": "movie",
    "tv": "tv",
    "book": "book",
    "audiobook": "search",
    "audioplay": "search",
    "music": "music",
}

NEWZNAB_SEARCH_TYPES: dict[str, str] = {
    "movie": "movie",
    "tv": "tvsearch",
    "book": "book",
    "audiobook": "search",
    "audioplay": "search",
    "music": "music",
}

GERMAN_CATEGORIES = {2140, 2145, 2150, 5140, 5145, 7120, 3130}
