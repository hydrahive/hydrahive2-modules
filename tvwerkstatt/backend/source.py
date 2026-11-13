"""Quelle des Startbildschirms, an einem festen Commit (PLAN-E1.md Baustein 4, SPEC Entscheidung 3).

Geholt und geprüft wird im Container. Aktualisiert wird nur durch eine neue Version dieses Moduls (später per Knopf mit
Anzeige der Änderungen), nie automatisch. Gelesen und für gut befunden: Probelauf 13.11.2026.
"""
from __future__ import annotations

from hydrahive.db.connection import db

REPO = "https://github.com/Gathin23/cleanyourtv"
COMMIT = "b95380483c9716b0bce6c151fa8de6b1f5000265"
LICENSE = "MIT"
PART = "launcher"
PACKAGE = "com.gathin.tvhome"
HOME = "/home/ubuntu"
SRC = f"{HOME}/src/cleanyourtv"
# Gradle 8.9: Wrapper-Jar laut gradle.org (gradle.org/release-checksums), Distribution wie im Wrapper festgenagelt.
WRAPPER_SHA256 = "498495120a03b9a6ab5d155f5de3c8f0d986a449153702fb80fc80e134484f17"
DIST_URL = r"distributionUrl=https\://services.gradle.org/distributions/gradle-8.9-bin.zip"
DIST_SHA256 = "d725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab"
RC_MISMATCH = 4                      # eigener Exit-Code: Stand oder Prüfsumme passt nicht

FETCH_SCRIPT = (
    f'set -eu; SRC={SRC}; '
    f'if [ "$(git -C "$SRC" rev-parse HEAD 2>/dev/null || true)" != "{COMMIT}" ]; then '
    'rm -rf "$SRC"; mkdir -p "$SRC"; cd "$SRC"; git init -q; '
    f"git remote add origin {REPO}; git fetch -q --depth 1 origin {COMMIT}; "
    "git -c advice.detachedHead=false checkout -q FETCH_HEAD; fi; "
    'cd "$SRC"; '
    f'[ "$(git rev-parse HEAD)" = "{COMMIT}" ] || {{ echo "Stand passt nicht" >&2; exit {RC_MISMATCH}; }}; '
    f'git diff --quiet HEAD || {{ echo "Quelle verändert" >&2; exit {RC_MISMATCH}; }}'
)

VERIFY_SCRIPT = (
    f"set -eu; cd {SRC}/launcher; "
    f'echo "{WRAPPER_SHA256}  gradle/wrapper/gradle-wrapper.jar" | sha256sum -c - >/dev/null '
    f'|| {{ echo "Gradle-Wrapper passt nicht zur Prüfsumme von gradle.org" >&2; exit {RC_MISMATCH}; }}; '
    f"grep -qxF '{DIST_URL}' gradle/wrapper/gradle-wrapper.properties "
    f'|| {{ echo "Gradle-Version unerwartet" >&2; exit {RC_MISMATCH}; }}; '
    f"grep -qxF 'distributionSha256Sum={DIST_SHA256}' gradle/wrapper/gradle-wrapper.properties "
    f'|| {{ echo "Gradle-Distribution nicht festgenagelt" >&2; exit {RC_MISMATCH}; }}'
)


def source_id() -> str:
    """Eintrag der Quelle (Repo + Commit + Lizenz) anlegen oder auf den aktuellen Stand bringen."""
    sid = "cleanyourtv"
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_sources (source_id, repo, commit_id, license) VALUES (?, ?, ?, ?) "
                     "ON CONFLICT(source_id) DO UPDATE SET commit_id = excluded.commit_id, "
                     "license = excluded.license, checked_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')",
                     (sid, REPO, COMMIT, LICENSE))
        conn.commit()
    return sid
