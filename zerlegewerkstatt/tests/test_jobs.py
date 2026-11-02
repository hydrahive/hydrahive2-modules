"""Analysejobs: seriell, wiederaufnahmefaehig und ohne Dubletten."""
from __future__ import annotations

from backend import jobs, store
from backend.runtime import CommandResult, RuntimeError_


class FakeRuntime:
    """Analyseumgebung, die ein festes Ergebnis liefert."""

    def __init__(self, *, payload=None, error=None):
        self.payload = payload if payload is not None else {"evidence": ["beobachtet"]}
        self.error = error
        self.calls: list[dict] = []

    def analyze(self, *, analysis_type, artifact, artifact_kind, token, timeout=900):
        self.calls.append({
            "analysis_type": analysis_type,
            "artifact": str(artifact),
            "artifact_kind": artifact_kind,
            "token": token,
        })
        if self.error:
            raise self.error
        return self.payload, CommandResult(returncode=0, stdout="{}", stderr="")


def create_case_with_artifact(client, alice) -> tuple[str, str]:
    from conftest import MOD_PREFIX
    from test_cases import body
    from test_uploads import PE_BYTES

    created = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body()).json()
    case_id = created["id"]
    upload = client.post(
        f"{MOD_PREFIX}/cases/{case_id}/artifacts", headers=alice,
        files=[("files", ("tool.exe", PE_BYTES, "application/octet-stream"))],
    )
    artifact_id = upload.json()["files"][0]["artifact_id"]
    return case_id, artifact_id


def test_job_wird_angelegt_und_doppelt_angelegte_werden_abgelehnt(client, alice):
    from conftest import MOD_PREFIX

    case_id, artifact_id = create_case_with_artifact(client, alice)
    first = client.post(f"{MOD_PREFIX}/cases/{case_id}/analyze", headers=alice,
                        json={"artifact_id": artifact_id, "analysis_type": "inspect-artifact"})
    assert first.status_code == 202
    assert first.json()["status"] == "queued"

    second = client.post(f"{MOD_PREFIX}/cases/{case_id}/analyze", headers=alice,
                         json={"artifact_id": artifact_id, "analysis_type": "inspect-artifact"})
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "reverse_job_already_running"


def test_unbekannter_analysetyp_wird_abgelehnt(client, alice):
    from conftest import MOD_PREFIX

    case_id, artifact_id = create_case_with_artifact(client, alice)
    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/analyze", headers=alice,
                           json={"artifact_id": artifact_id, "analysis_type": "rm -rf /"})
    assert response.status_code == 422


def test_analysetyp_muss_zum_artefakt_passen(client, alice):
    from conftest import MOD_PREFIX
    from test_cases import body
    from test_uploads import PE_BYTES

    created = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body()).json()
    upload = client.post(
        f"{MOD_PREFIX}/cases/{created['id']}/artifacts", headers=alice,
        files=[("files", ("app.apk", PE_BYTES, "application/octet-stream"))],
    )
    artifact_id = upload.json()["files"][0]["artifact_id"]
    response = client.post(f"{MOD_PREFIX}/cases/{created['id']}/analyze", headers=alice,
                           json={"artifact_id": artifact_id,
                                 "analysis_type": "inspect-android-package"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "reverse_analysis_type_not_allowed"


def test_analyse_braucht_projektzugriff(client, alice, bob):
    from conftest import MOD_PREFIX

    case_id, artifact_id = create_case_with_artifact(client, alice)
    denied = client.post(f"{MOD_PREFIX}/cases/{case_id}/analyze", headers=bob,
                         json={"artifact_id": artifact_id, "analysis_type": "inspect-artifact"})
    assert denied.status_code == 404


def test_job_laeuft_durch_und_legt_ergebnis_ab(client, alice):
    from conftest import MOD_PREFIX

    case_id, artifact_id = create_case_with_artifact(client, alice)
    created = client.post(f"{MOD_PREFIX}/cases/{case_id}/analyze", headers=alice,
                          json={"artifact_id": artifact_id, "analysis_type": "inspect-artifact"})
    job_id = created.json()["id"]

    runtime = FakeRuntime()
    runner = jobs.JobRunner(runtime=runtime)
    job = runner.run_job(job_id)

    assert job["status"] == "done"
    assert job["progress"] == 100
    assert job["result_path"].startswith("results/")
    assert runtime.calls[0]["analysis_type"] == "inspect-artifact"


def test_fehlgeschlagene_analyse_wird_gemeldet(client, alice):
    from conftest import MOD_PREFIX

    case_id, artifact_id = create_case_with_artifact(client, alice)
    created = client.post(f"{MOD_PREFIX}/cases/{case_id}/analyze", headers=alice,
                          json={"artifact_id": artifact_id, "analysis_type": "inspect-artifact"})
    job_id = created.json()["id"]

    runtime = FakeRuntime(error=RuntimeError_("analysis_timeout"))
    runner = jobs.JobRunner(runtime=runtime)
    job = runner.run_job(job_id)

    assert job["status"] == "failed"
    assert job["error_code"] == "reverse_analysis_timeout"


def test_neustart_markiert_laufende_jobs_als_unterbrochen(client, alice):
    from conftest import MOD_PREFIX

    case_id, artifact_id = create_case_with_artifact(client, alice)
    created = client.post(f"{MOD_PREFIX}/cases/{case_id}/analyze", headers=alice,
                          json={"artifact_id": artifact_id, "analysis_type": "inspect-artifact"})
    job_id = created.json()["id"]
    store.update_job(job_id, status="running")

    runner = jobs.JobRunner(runtime=FakeRuntime())
    assert runner.recover() == 1

    job = store.get_job(job_id)
    assert job["status"] == "interrupted"
    assert job["error_code"] == "reverse_job_interrupted"


def test_ergebnis_der_analyse_ist_lesbar(client, alice):
    from conftest import MOD_PREFIX

    case_id, artifact_id = create_case_with_artifact(client, alice)
    created = client.post(f"{MOD_PREFIX}/cases/{case_id}/analyze", headers=alice,
                          json={"artifact_id": artifact_id, "analysis_type": "inspect-artifact"})
    job_id = created.json()["id"]
    runner = jobs.JobRunner(runtime=FakeRuntime(payload={"evidence": ["a", "b"]}))
    runner.run_job(job_id)

    response = client.get(f"{MOD_PREFIX}/cases/{case_id}/report", headers=alice)
    assert response.status_code == 200
    body = response.json()
    assert body["observed"], "Beobachtungen fehlen"
    assert body["jobs"][0]["status"] == "done"


def test_runtime_status_wird_gemeldet(client, alice):
    from conftest import MOD_PREFIX

    response = client.get(f"{MOD_PREFIX}/runtime/status", headers=alice)
    assert response.status_code == 200
    assert "available" in response.json()
