"""Laden von gesetze-im-internet.de (Spec §4.1, Plan L1 Schritt 4).

- Nur ``https://www.gesetze-im-internet.de``; URL wird aus dem Kürzel gebaut. Die toc verlinkt ``http://`` mit
  302 auf https (geprüft 20.10.2026) – der SSRF-Client des Kerns folgt Redirects nicht, also gleich https.
- Kürzel nur ``[a-z0-9_]`` (wie in der toc), sonst kein Request.
- ZIP nur im Speicher öffnen (kein Entpacken auf Platte → kein Zip-Slip); genau eine XML-Datei; Größenlimits.
"""
from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree as ET

import httpx

HOST = "https://www.gesetze-im-internet.de"
TOC_URL = f"{HOST}/gii-toc.xml"
MAX_ZIP_BYTES = 20_000_000          # größtes Gesetz der Kernliste: StVO 742 KB (L0)
MAX_XML_BYTES = 80_000_000
TIMEOUT = 60.0
USER_AGENT = "HydraHive-Recht/0.1 (privat; Gesetze im Internet XML)"
_KEY = re.compile(r"[a-z0-9_]{1,80}")
_TOC_LINK = re.compile(r"^https?://www\.gesetze-im-internet\.de/([a-z0-9_]{1,80})/xml\.zip$")


class FetchError(RuntimeError):
    pass


def zip_url(key: str) -> str:
    if not _KEY.fullmatch(key or ""):
        raise FetchError(f"Ungültiges Gesetzeskürzel: {key!r}")
    return f"{HOST}/{key}/xml.zip"


async def _get(url: str):
    from hydrahive.net.ssrf import SsrfBlocked, safe_async_client
    try:
        async with safe_async_client(url, timeout=TIMEOUT) as client:
            return await client.get(url, headers={"User-Agent": USER_AGENT})
    except SsrfBlocked as e:
        raise FetchError(f"Adresse gesperrt: {e}") from None
    except httpx.HTTPError as e:               # Zeitüberschreitung, Verbindung, Protokoll …
        raise FetchError(f"Nicht erreichbar ({type(e).__name__})") from None


async def fetch_toc() -> dict[str, str]:
    """Kürzel → Titel aller Gesetze im amtlichen Inhaltsverzeichnis."""
    r = await _get(TOC_URL)
    if r.status_code != 200:
        raise FetchError(f"Inhaltsverzeichnis: HTTP {r.status_code}")
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        raise FetchError("Inhaltsverzeichnis nicht lesbar") from None
    out: dict[str, str] = {}
    for item in root.iter("item"):
        m = _TOC_LINK.match((item.findtext("link") or "").strip())
        if m:
            out[m.group(1)] = (item.findtext("title") or "").strip()
    return out


async def fetch_law_xml(key: str) -> bytes:
    url = zip_url(key)
    r = await _get(url)
    if r.status_code != 200:
        raise FetchError(f"HTTP {r.status_code}")
    if len(r.content) > MAX_ZIP_BYTES:
        raise FetchError(f"Download zu groß ({len(r.content)} Bytes)")
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        xmls = [i for i in z.infolist() if i.filename.lower().endswith(".xml") and not i.is_dir()]
    except zipfile.BadZipFile:
        raise FetchError("Kein gültiges ZIP") from None
    if len(xmls) != 1:
        raise FetchError(f"ZIP enthält {len(xmls)} XML-Dateien statt einer")
    if xmls[0].file_size > MAX_XML_BYTES:
        raise FetchError(f"XML zu groß ({xmls[0].file_size} Bytes)")
    data = z.read(xmls[0])
    if len(data) > MAX_XML_BYTES:
        raise FetchError("XML zu groß")
    return data
