from __future__ import annotations

INDEXER_API_URL = "https://treasure-maps.com/api"
INDEXER_ORIGIN = "https://treasure-maps.com"
INDEXER_CREDENTIAL = "tresuere_token"

MAX_CREDENTIAL_LENGTH = 4096
MAX_QUERY_LENGTH = 200
MAX_RESULTS = 100
MAX_XML_BYTES = 4 * 1024 * 1024
MAX_TITLE_LENGTH = 512
INDEXER_TIMEOUT_SECONDS = 15.0
RESULT_TTL_SECONDS = 15 * 60

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
