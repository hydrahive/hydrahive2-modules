from __future__ import annotations

from fastapi import APIRouter

from hydrahive.settings import settings

from . import state

router = APIRouter()


def data_dir():
    return settings.data_dir / "vitrine"


@router.get("/status")
def get_status() -> dict:
    """Dienst läuft? Display verbunden? Bildrate, aktuelles Video. Zugriff regelt das Modul-Tor (module.vitrine)."""
    return state.read(data_dir())
