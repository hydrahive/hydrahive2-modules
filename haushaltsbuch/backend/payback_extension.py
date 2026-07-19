"""Reproducible in-memory packaging of the constant browser-extension source."""

from __future__ import annotations

import base64
import hashlib
import io
import zipfile
from pathlib import Path

from fastapi import status
from hydrahive.api.middleware.errors import coded

EXTENSION_DIR = (
    Path(__file__).resolve().parents[1] / "browser-extension" / "payback-bridge"
)
_FILENAME = "hydrahive-payback-bridge.zip"
_MAX_FILES = 100
_MAX_FILE_BYTES = 5 * 1024 * 1024
_MAX_TOTAL_BYTES = 20 * 1024 * 1024


def build_package() -> dict:
    if not EXTENSION_DIR.is_dir():
        raise coded(
            status.HTTP_503_SERVICE_UNAVAILABLE, "payback_extension_unavailable"
        )
    files = sorted(path for path in EXTENSION_DIR.rglob("*") if path.is_file())
    if not files or len(files) > _MAX_FILES:
        raise coded(
            status.HTTP_503_SERVICE_UNAVAILABLE, "payback_extension_unavailable"
        )
    total = 0
    output = io.BytesIO()
    with zipfile.ZipFile(
        output, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in files:
            if path.is_symlink():
                raise coded(
                    status.HTTP_503_SERVICE_UNAVAILABLE, "payback_extension_unavailable"
                )
            content = path.read_bytes()
            total += len(content)
            if len(content) > _MAX_FILE_BYTES or total > _MAX_TOTAL_BYTES:
                raise coded(
                    status.HTTP_503_SERVICE_UNAVAILABLE, "payback_extension_unavailable"
                )
            relative = path.relative_to(EXTENSION_DIR).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )
    payload = output.getvalue()
    return {
        "filename": _FILENAME,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "base64": base64.b64encode(payload).decode("ascii"),
    }
