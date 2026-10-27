"""Zugriff auf die Musik-Freigabe – nur lesen (Plex nutzt sie mit). SPEC „Einlesen“.

smbprotocol (Kern-Abhängigkeit) ohne Einbinden und ohne root. Das Passwort kommt aus dem Safe des Eintragenden und
lebt nur im Speicher dieser Verbindung – nie in DB, Log oder Antwort.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from hydrahive.credentials.store import get_credential

logger = logging.getLogger(__name__)

_HOST = re.compile(r"^[A-Za-z0-9._-]{1,253}$")
_PART = re.compile(r"^[^\x00-\x1f/\\:*?\"<>|]{1,255}$")


class SourceError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SmbUrl:
    host: str
    share: str
    base: str          # Unterordner ohne führenden/abschließenden Schrägstrich, "" = ganze Freigabe


def parse_url(url: str) -> SmbUrl:
    """smb://host/freigabe[/unterordner] → SmbUrl, sonst SourceError(radiostream_url_invalid)."""
    u = urlparse((url or "").strip())
    parts = [unquote(p) for p in (u.path or "").split("/") if p]
    if u.scheme != "smb" or not u.hostname or not _HOST.match(u.hostname) or u.username or u.password \
            or not parts or any(p in (".", "..") or not _PART.match(p) for p in parts):
        raise SourceError("radiostream_url_invalid")
    return SmbUrl(host=u.hostname, share=parts[0], base="/".join(parts[1:]))


def credential_pair(owner: str, name: str | None) -> tuple[str, str]:
    """(benutzer, passwort) aus einem basic-Eintrag im Safe von `owner`."""
    cred = get_credential(owner, name) if name else None
    if cred is None or cred.type != "basic":
        raise SourceError("radiostream_credential_invalid")
    user, _, password = cred.value.partition(":")
    return user, password


def open_source(url: str, owner: str, credential_name: str | None):
    """Verbindung zur Freigabe (mit walk/open/top_dirs/close)."""
    u = parse_url(url)
    user, password = credential_pair(owner, credential_name)
    return _connect(u.host, u.share, user, password, u.base)


def _connect(host: str, share: str, user: str, password: str, base: str = ""):
    return _SmbConn(host, share, user, password, base)


def _map_error(exc: Exception) -> SourceError:
    text = f"{type(exc).__name__} {exc}".lower()
    if "logon" in text or "access_denied" in text or "access is denied" in text or "authentication" in text:
        return SourceError("radiostream_auth_failed")
    if "bad_network_name" in text or "object_name_not_found" in text or "object_path_not_found" in text:
        return SourceError("radiostream_share_not_found")
    return SourceError("radiostream_source_unreachable")


class _SmbConn:
    def __init__(self, host: str, share: str, user: str, password: str, base: str):
        import smbclient  # aus smbprotocol
        self._smb = smbclient
        self._host = host
        self._root = rf"\\{host}\{share}" + ("\\" + base.replace("/", "\\") if base else "")
        try:
            smbclient.register_session(host, username=user, password=password, connection_timeout=15)
            smbclient.listdir(self._root)
        except Exception as exc:  # noqa: BLE001 – Fehler des Fremdsystems → verständlicher Code
            logger.info("Radiostream: Verbindung zu %s fehlgeschlagen: %s", host, type(exc).__name__)
            raise _map_error(exc) from None

    def _abs(self, rel: str) -> str:
        return self._root + ("\\" + rel.replace("/", "\\") if rel else "")

    def top_dirs(self) -> list[str]:
        return sorted(e.name for e in self._smb.scandir(self._root) if e.is_dir())

    def walk(self):
        """(rel_dir, [(name, size, mtime_int), …]) je Ordner, Ordner in fester Reihenfolge."""
        stack = [""]
        while stack:
            rel = stack.pop()
            files, dirs = [], []
            try:
                entries = list(self._smb.scandir(self._abs(rel)))
            except OSError as exc:
                logger.info("Radiostream: Ordner nicht lesbar (%s): %s", rel or "/", type(exc).__name__)
                continue
            for e in entries:
                if e.is_dir():
                    dirs.append(f"{rel}/{e.name}" if rel else e.name)
                elif e.is_file():
                    st = e.stat()
                    files.append((e.name, int(st.st_size), int(st.st_mtime)))
            yield rel, sorted(files)
            stack.extend(sorted(dirs, reverse=True))

    def open(self, rel_path: str):
        return self._smb.open_file(self._abs(rel_path), mode="rb")

    def close(self) -> None:
        try:
            self._smb.delete_session(self._host)
        except Exception:  # noqa: BLE001 – Aufräumen darf nie stören
            pass
