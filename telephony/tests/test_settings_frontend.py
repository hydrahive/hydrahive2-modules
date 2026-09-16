from __future__ import annotations

from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
FRONTEND = MODULE_DIR / "frontend"


def test_settings_section_renders_registration_probe_form() -> None:
    page = (FRONTEND / "VoIPPage.tsx").read_text()
    settings = (FRONTEND / "RegistrationProbeSettings.tsx").read_text()

    assert 'active === "settings"' in page
    assert "<RegistrationProbeSettings" in page
    assert 'type="password"' in settings
    assert 'autoComplete="off"' in settings
    assert settings.count("readOnly") == 2
    assert "telephonyApi.testRegistration" in settings


def test_registration_probe_frontend_never_persists_credentials() -> None:
    source = "\n".join(
        path.read_text()
        for path in FRONTEND.glob("*.tsx")
        if path.name in {"RegistrationProbeSettings.tsx", "VoIPPage.tsx"}
    )

    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "URLSearchParams" not in source
    assert 'setPassword("")' in source


def test_registration_probe_api_uses_json_post_body() -> None:
    source = (FRONTEND / "api.ts").read_text()

    assert '"/modules/telephony/spike/registration-test"' in source
    assert "api.post<RegistrationProbeResponse>" in source
