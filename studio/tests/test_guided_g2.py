"""Studio G2: Figuren & Orte mit Probebild (studio/SPEC.md „Bauplan G2“). Der Bild-Anbieter wird ersetzt."""
from __future__ import annotations

import time

from _gen_helpers import PNG, P, provider  # noqa: F401  (Fixture)
from conftest import MOD_PREFIX, OTHER_PROJECT_ID


def _el(client, h, ws, *, refs: bool = True, desc: str = "five friendly heads", kind: str = "character", name: str = "Hydra") -> dict:
    r = []
    if refs:
        (ws / "fotos").mkdir(exist_ok=True)
        (ws / "fotos/h.png").write_bytes(PNG)
        r = ["fotos/h.png"]
    return client.post(f"{P}/elements", headers=h, json={"kind": kind, "name": name, "description": desc, "references": r}).json()


def _wait(client, h, target: str, timeout: float = 5.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        jobs = [j for j in client.get(f"{P}/jobs", headers=h).json()["jobs"] if j["target"] == target]
        if jobs and jobs[0]["status"] in ("done", "failed"):
            return jobs[0]
        time.sleep(0.05)
    raise AssertionError("Auftrag nicht fertig")


def _get(client, h, el_id: str) -> dict:
    return next(e for e in client.get(P, headers=h).json()["elements"] if e["id"] == el_id)


def test_new_element_has_guided_fields(client, auth_headers, ws) -> None:
    el = _el(client, auth_headers, ws)
    assert el["probe_rel"] == "" and el["approved"] is False and el["no_photo"] is False


def test_probe_from_photo(client, auth_headers, ws, provider) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"image": "test/bild"}, "look": {"style": "watercolor", "palette": []}})
    el = _el(client, auth_headers, ws)
    r = client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "probe" and r.json()["target"] == el["id"]
    job = _wait(client, auth_headers, el["id"])
    assert job["status"] == "done", job
    got = _get(client, auth_headers, el["id"])
    assert got["probe_rel"].startswith("studio/media/probes/") and (ws / got["probe_rel"]).is_file()
    assert got["approved"] is False
    call = provider.calls[0]
    assert call["model"] == "test/bild" and call["aspect_ratio"] == "16:9"
    assert len(call["references"]) == 1 and call["references"][0].startswith("data:image/png;base64,")
    for needle in ("watercolor", "Hydra", "five friendly heads"):
        assert needle in call["prompt"], needle
    lib = client.get(f"{MOD_PREFIX}/projects/test-project-studio/library", headers=auth_headers).json()["items"]
    assert any(i["rel"] == got["probe_rel"] and i["source"] == "studio_probe" for i in lib)


def test_probe_place_wording(client, auth_headers, ws, provider) -> None:
    el = _el(client, auth_headers, ws, kind="place", name="Leuchtturm", desc="white tower")
    client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    _wait(client, auth_headers, el["id"])
    assert "Establishing view" in provider.calls[0]["prompt"] and "Leuchtturm" in provider.calls[0]["prompt"]


def test_probe_without_photo_uses_description(client, auth_headers, ws, provider) -> None:
    el = _el(client, auth_headers, ws, refs=False)
    assert client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers).status_code == 202
    _wait(client, auth_headers, el["id"])
    assert provider.calls[0]["references"] == []


def test_probe_needs_something(client, auth_headers, ws, provider) -> None:
    el = _el(client, auth_headers, ws, refs=False, desc="")
    r = client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_probe_nothing"
    assert provider.calls == []


def test_probe_unknown_or_foreign(client, auth_headers, ws) -> None:
    assert client.post(f"{P}/elements/{'a' * 32}/probe", headers=auth_headers).status_code == 404
    r = client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/plan/elements/{'a' * 32}/probe", headers=auth_headers)
    assert r.status_code == 404


def test_probe_busy(client, auth_headers, ws, monkeypatch) -> None:
    from _gen_helpers import FakeProvider
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(delay=0.5))
    el = _el(client, auth_headers, ws)
    assert client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers).status_code == 202
    r = client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "studio_probe_running"
    _wait(client, auth_headers, el["id"])


def test_probe_failure_is_shown(client, auth_headers, ws, monkeypatch) -> None:
    from _gen_helpers import FakeProvider
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(error="no_key"))
    el = _el(client, auth_headers, ws)
    client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    job = _wait(client, auth_headers, el["id"])
    assert job["status"] == "failed" and job["error"] == "no_key"
    assert _get(client, auth_headers, el["id"])["probe_rel"] == ""


def test_approve_needs_probe_and_new_probe_resets(client, auth_headers, ws, provider) -> None:
    el = _el(client, auth_headers, ws)
    r = client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={**el, "approved": True})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_probe_missing"
    client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    _wait(client, auth_headers, el["id"])
    cur = _get(client, auth_headers, el["id"])
    assert client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={**cur, "approved": True}).json()["approved"] is True
    first = cur["probe_rel"]
    client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    _wait(client, auth_headers, el["id"])
    again = _get(client, auth_headers, el["id"])
    assert again["approved"] is False and again["probe_rel"] != first
    assert (ws / first).is_file()                                                     # altes bleibt in der Sammlung


def test_profi_save_keeps_guided_fields(client, auth_headers, ws, provider) -> None:
    el = _el(client, auth_headers, ws)
    client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    _wait(client, auth_headers, el["id"])
    cur = _get(client, auth_headers, el["id"])
    client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={**cur, "approved": True})
    # Profi-Ansicht schickt nur ihre Felder
    client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={"kind": "character", "name": "Hydra", "description": "neu",
                                                                        "style_anchor": "", "palette": [], "references": cur["references"]})
    after = _get(client, auth_headers, el["id"])
    assert after["probe_rel"] == cur["probe_rel"] and after["approved"] is True and after["description"] == "neu"


def test_probe_rel_cannot_be_set_freely(client, auth_headers, ws) -> None:
    (ws / "fremd.png").write_bytes(PNG)
    el = _el(client, auth_headers, ws)
    out = client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={**el, "probe_rel": "fremd.png"}).json()
    assert out["probe_rel"] == ""


def test_no_photo_flag_and_bool_only(client, auth_headers, ws) -> None:
    el = _el(client, auth_headers, ws, refs=False)
    assert client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={**el, "no_photo": True}).json()["no_photo"] is True
    assert client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={**el, "no_photo": "ja"}).json()["no_photo"] is False


def test_approved_probe_goes_first_into_shot_images(client, auth_headers, ws, provider) -> None:
    el = _el(client, auth_headers, ws)
    client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    _wait(client, auth_headers, el["id"])
    cur = _get(client, auth_headers, el["id"])
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Wald", "element_ids": [el["id"]]}).json()
    shot = client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "Hydra im Wald", "element_ids": [el["id"]]}).json()

    def refs_of_next_image() -> list[str]:
        n = len(provider.calls)
        client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers)
        _wait(client, auth_headers, shot["id"])
        return provider.calls[n]["references"]

    assert len(refs_of_next_image()) == 1                                             # nicht freigegeben: nur das Foto
    client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={**cur, "approved": True})
    refs = refs_of_next_image()
    probe = (ws / cur["probe_rel"]).read_bytes()
    import base64
    assert len(refs) == 2 and refs[0].endswith(base64.b64encode(probe).decode())    # Probebild zuerst, dann das Foto


def test_media_delete_clears_probe(client, auth_headers, ws, provider) -> None:
    el = _el(client, auth_headers, ws)
    client.post(f"{P}/elements/{el['id']}/probe", headers=auth_headers)
    _wait(client, auth_headers, el["id"])
    cur = _get(client, auth_headers, el["id"])
    client.put(f"{P}/elements/{el['id']}", headers=auth_headers, json={**cur, "approved": True})
    use = client.get(f"{MOD_PREFIX}/projects/test-project-studio/media/usage", headers=auth_headers, params={"rel": cur["probe_rel"]}).json()
    assert use["own"] is True and [e["id"] for e in use["elements"]] == [el["id"]]
    r = client.request("DELETE", f"{MOD_PREFIX}/projects/test-project-studio/media", headers=auth_headers, params={"rel": cur["probe_rel"]})
    assert r.status_code == 200, r.text
    after = _get(client, auth_headers, el["id"])
    assert after["probe_rel"] == "" and after["approved"] is False
