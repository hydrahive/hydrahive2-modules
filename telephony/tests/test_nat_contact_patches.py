from __future__ import annotations

from pathlib import Path


TELEPHONY_ROOT = Path(__file__).resolve().parents[1]
PATCH_ROOT = TELEPHONY_ROOT / "patches"
PREPARE_RUNTIME = TELEPHONY_ROOT / "spike" / "prepare-runtime.sh"


def test_libre_patch_is_opt_in_udp_rport_contact_with_upstream_test() -> None:
    patch = (PATCH_ROOT / "libre-rport-contact.patch").read_text(encoding="utf-8")

    assert "sipreg_enable_rport_contact" in patch
    assert "sipreg_contact_addr" in patch
    assert 'msg_param_decode(&msg->via.params, "received"' in patch
    assert 'msg_param_decode(&msg->via.params, "rport"' in patch
    assert "msg->tp != SIP_TRANSP_UDP" in patch
    assert "test_sipreg_rport_contact" in patch
    assert "request destination" in patch


def test_baresip_patch_exposes_received_mode_and_dialog_contact_test() -> None:
    patch = (PATCH_ROOT / "baresip-rport-contact.patch").read_text(encoding="utf-8")

    assert 'str_casecmp(sipnat, "received")' in patch
    assert "sipreg_enable_rport_contact(reg->sipreg, true)" in patch
    assert "ua_nat_contact_set" in patch
    assert '"sip:%s@%J"' in patch
    assert '"sip:x@127.0.0.1:"' in patch


def test_sidecar_build_applies_patches_to_pinned_sources_and_runs_tests() -> None:
    script = PREPARE_RUNTIME.read_text(encoding="utf-8")

    assert 'readonly PATCH_DIR="$SCRIPT_DIR/../patches"' in script
    assert "libre-rport-contact.patch" in script
    assert "baresip-rport-contact.patch" in script
    assert script.count("apply --check") == 2
    assert "test_sipreg_rport_contact" in script
    assert "test_account_sipnat_received test_ua_alloc test_ua_register" in script
