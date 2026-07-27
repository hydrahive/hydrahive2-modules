from __future__ import annotations

from pathlib import Path

FRONTEND = Path(__file__).parents[1] / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_canonical_frontend_is_a_cockpit_module() -> None:
    index = _read("index.tsx")
    assert 'path: "/mediacenter"' in index
    assert "cockpit: true" in index
    assert "Radarr" not in index
    assert "Sonarr" not in index


def test_frontend_api_uses_only_the_v1_mediacenter_routes() -> None:
    source = _read("api.ts")
    for route in (
        '`${BASE}/status`',
        '`${BASE}/connections/test`',
        '`${BASE}/search`',
        '`${BASE}/enqueue`',
        '`${BASE}/queue`',
        '`${BASE}/history`',
    ):
        assert route in source
    assert "http://" not in source
    assert "https://" not in source


def test_frontend_renders_all_v1_views_without_destructive_actions() -> None:
    page = _read("MediacenterPage.tsx")
    # V2.1: ConnectionStatus ist im SettingsPanel aufgegangen — alle Dienste an
    # EINER Stelle statt einer Statusleiste ueber jeder Ansicht.
    assert "SettingsPanel" in page
    assert "SearchPanel" in page
    # V2: ResultGrid kapselt die Poster- UND die Listenansicht (ResultList).
    assert "ResultGrid" in page
    assert "ResultList" in _read("ResultGrid.tsx")
    assert "JobsPanel" in page
    combined = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.glob("*.tsx"))
    assert "mediacenterApi.enqueue" in combined
    assert "mediacenterApi.queue" in combined
    assert "mediacenterApi.history" in combined
    assert "mediacenterApi.cancel" not in combined
    assert "mediacenterApi.delete" not in combined


# --- V2: Cover-Oberflaeche und Sprachsuche ---------------------------------

def test_poster_grid_zeigt_cover_ohne_referrer_zu_lecken() -> None:
    """referrerPolicy verhindert, dass HydraHive-URLs an den Bildhost gehen."""
    for name in ("PosterCard.tsx", "GroupDetail.tsx"):
        source = _read(name)
        assert "<img" in source
        assert 'referrerPolicy="no-referrer"' in source


def test_cover_bilder_werden_lazy_geladen() -> None:
    assert 'loading="lazy"' in _read("PosterCard.tsx")


def test_poster_hat_einen_fallback_ohne_cover() -> None:
    """Buecher liefert der Indexer ohne Cover — das Raster darf nicht loechrig
    werden und ein kaputtes Bild nichts zerstoeren."""
    source = _read("PosterCard.tsx")
    assert "onError" in source
    assert "broken" in source


def test_detailansicht_behaelt_die_v1_freigabelogik() -> None:
    """V2 aendert nur die Darstellung — nie die Entscheidung, was erlaubt ist."""
    source = _read("GroupDetail.tsx")
    assert 'decision === "eligible"' in source
    assert "result_id" in source
    assert "mediacenterApi.enqueue" in source


def test_spracheingabe_ist_optional_und_clientseitig() -> None:
    """Kein Audio-Upload, kein toter Knopf ohne Browser-Unterstuetzung."""
    hook = _read("useSpeechInput.ts")
    assert "webkitSpeechRecognition" in hook
    assert "supported" in hook
    assert "fetch(" not in hook, "Spracheingabe darf nichts hochladen"
    panel = _read("SearchPanel.tsx")
    assert "speech.supported &&" in panel, "Mikrofon nur bei Unterstuetzung zeigen"


def test_navigation_wirbt_nicht_mit_fremdprodukten() -> None:
    """Der Nav-/Modul-Eintrag bleibt produktneutral.

    Ab V2.1 sind Radarr/Sonarr echte Bestandteile und werden in der
    Einstellungsansicht namentlich genannt — das ist gewollt. Verboten bleibt
    nur, das Modul selbst darueber zu benennen oder zu bewerben.
    """
    index = _read("index.tsx")
    assert "Radarr" not in index
    assert "Sonarr" not in index


# --- V2.1: Einstellungen an einer Stelle -----------------------------------

def test_einstellungen_sind_ein_eigener_bereich() -> None:
    page = _read("MediacenterPage.tsx")
    assert '"settings"' in page
    assert "SettingsPanel" in page


def test_settings_zeigt_alle_vier_dienste() -> None:
    """Tills Beschwerde: Radarr/Sonarr wurden nirgends angezeigt."""
    source = _read("SettingsPanel.tsx")
    for name in ("indexer", "sab", "Radarr", "Sonarr"):
        assert name in source


def test_settings_verweist_auf_den_credential_store() -> None:
    """Es darf keinen zweiten Ort fuer Adressen geben — die Seite verlinkt zum
    Pflegen, statt eigene Eingabefelder anzubieten."""
    source = _read("SettingsPanel.tsx")
    assert "/credentials" in source
    for credential in ("tresuere_token", "sabnzb_token", "radarr_token", "sonarr_token"):
        assert credential in source


def test_settings_hat_keine_eigenen_adressfelder() -> None:
    """Kein Formular, das Adressen doppelt speichern koennte."""
    source = _read("SettingsPanel.tsx")
    assert "<input" not in source
    assert "onSubmit" not in source


def test_zusatzdienste_sind_als_optional_gekennzeichnet() -> None:
    """Radarr/Sonarr duerfen nicht wie ein Fehler aussehen, wenn sie fehlen."""
    assert "optional" in _read("SettingsPanel.tsx")


# --- V3: Uebergabe an Radarr/Sonarr ----------------------------------------

def test_uebergabe_knopf_existiert_und_ist_typgebunden() -> None:
    source = _read("ArrHandoffButton.tsx")
    assert "movie: \"radarr\"" in source
    assert "tv: \"sonarr\"" in source


def test_uebergabe_nur_bei_konfiguriertem_dienst_und_freigegebener_fassung() -> None:
    """Kein toter Knopf, und die V1-Profilpruefung gilt weiter."""
    source = _read("ArrHandoffButton.tsx")
    assert "!configured" in source
    assert 'release.decision !== "eligible"' in source


def test_uebergabe_erkennt_fehlercode_nicht_uebersetzten_text() -> None:
    """Der Nachfrage-Dialog haengt am Rohcode — uebersetzter Text aendert sich."""
    source = _read("ArrHandoffButton.tsx")
    assert 'errorCode(cause) === "arr_target_required"' in source


def test_direktweg_an_sabnzbd_bleibt_erhalten() -> None:
    """Buecher/Hoerbuecher/Musik kennen Radarr/Sonarr nicht."""
    source = _read("GroupDetail.tsx")
    assert "mediacenterApi.enqueue" in source
    assert "ArrHandoffButton" in source


def test_frontend_nutzt_nur_bekannte_arr_routen() -> None:
    source = _read("api.ts")
    assert "/arr/${service}/targets" in source
    assert "/arr/handoff" in source
    assert "http://" not in source
    assert "https://" not in source
