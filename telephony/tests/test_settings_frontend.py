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
    assert "telephonyApi.testIncomingCall" in settings
    assert 'testingMode === "incoming"' in settings
    assert 't("probe.incoming_instruction")' in settings


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
    assert '"/modules/telephony/spike/incoming-test"' in source
    assert "testIncomingCall" in source
    assert "api.post<RegistrationProbeResponse>" in source


def test_incoming_probe_frontend_declares_all_stable_outcomes_and_texts() -> None:
    types = (FRONTEND / "types.ts").read_text()
    translations = (FRONTEND / "i18n.ts").read_text()

    for outcome in (
        "incoming_answered",
        "no_incoming_call",
        "caller_cancelled",
        "answer_failed",
    ):
        assert f'| "{outcome}"' in types
        assert f"{outcome}:" in translations
