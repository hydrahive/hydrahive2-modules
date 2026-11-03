"""Agentenwerkzeuge: Projektbindung, Grenzen und nicht vertrauenswuerdiger Inhalt."""
from __future__ import annotations

from pathlib import Path

import pytest
from hydrahive.tools.base import ToolContext

from backend import tools
from backend.tools import ALL_TOOLS

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID


def ctx_for(user: str = "alice", project_id: str | None = PROJECT_ID) -> ToolContext:
    return ToolContext(
        session_id="s1",
        agent_id="a1",
        user_id=user,
        workspace=Path("/tmp"),
        project_id=project_id,
    )


def create_case(client, alice, project_id: str = PROJECT_ID) -> str:
    from test_cases import body

    created = client.post(f"{MOD_PREFIX}/cases", headers=alice,
                          json=body(project_id=project_id)).json()
    return created["id"]


def upload_artifact(client, alice, case_id: str) -> str:
    from test_uploads import PE_BYTES

    response = client.post(
        f"{MOD_PREFIX}/cases/{case_id}/artifacts", headers=alice,
        files=[("files", ("tool.exe", PE_BYTES, "application/octet-stream"))],
    )
    return response.json()["files"][0]["artifact_id"]


def test_es_gibt_genau_drei_werkzeuge():
    assert len(ALL_TOOLS) == 3
    assert {tool.name for tool in ALL_TOOLS} == {
        "reverse_cases", "reverse_inspect", "reverse_report"}


def test_kein_werkzeug_nimmt_pfade_befehle_oder_urls_entgegen():
    verboten = ("path", "file", "command", "cmd", "url", "uri", "host", "shell", "exec")
    for tool in ALL_TOOLS:
        for name in tool.schema.get("properties", {}):
            assert not any(word in name.lower() for word in verboten), \
                f"{tool.name} nimmt {name} entgegen"


def test_reverse_inspect_erlaubt_nur_analysetypen():
    schema = next(t for t in ALL_TOOLS if t.name == "reverse_inspect").schema
    assert schema["properties"]["analysis_type"]["enum"] == [
        "inspect-artifact",
        "inspect-android-package",
        "inspect-managed-artifact",
        "inspect-managed-members",
        "inspect-pcap-capture",
        "inspect-byte-entropy",
        "inspect-native-exports",
        "inspect-pe-imports",
        "inspect-pe-resources",
        "inspect-pe-load-config",
        "inspect-pe-certificates",
        "inspect-elf-notes",
        "inspect-go-binary",
        "inspect-rust-binary",
        "inspect-kernel-module",
        "inspect-apk-signature",
        "inspect-firmware-regions",
        "analyze-ghidra",
    ]
    assert set(schema["required"]) == {"case_id", "artifact_id", "analysis_type"}


@pytest.mark.asyncio
async def test_reverse_cases_zeigt_nur_das_eigene_projekt(client, alice, bob):
    mine = create_case(client, alice, PROJECT_ID)
    theirs = create_case(client, bob, OTHER_PROJECT_ID)

    result = await tools.CASES_TOOL.execute({}, ctx_for("alice", PROJECT_ID))
    assert result.success is True
    ids = [row["case_id"] for row in result.output]
    assert mine in ids
    assert theirs not in ids


@pytest.mark.asyncio
async def test_reverse_cases_ohne_projekt_scheitert():
    result = await tools.CASES_TOOL.execute({}, ctx_for("alice", None))
    assert result.success is False
    assert result.error == "reverse_project_missing"


@pytest.mark.asyncio
async def test_reverse_cases_fremdes_projekt_scheitert(client, bob):
    create_case(client, bob, OTHER_PROJECT_ID)
    result = await tools.CASES_TOOL.execute({}, ctx_for("alice", OTHER_PROJECT_ID))
    assert result.success is False
    assert result.error == "reverse_project_not_found"


@pytest.mark.asyncio
async def test_reverse_inspect_startet_eine_analyse(client, alice):
    case_id = create_case(client, alice)
    artifact_id = upload_artifact(client, alice, case_id)

    result = await tools.INSPECT_TOOL.execute(
        {"case_id": case_id, "artifact_id": artifact_id,
         "analysis_type": "inspect-managed-artifact"},
        ctx_for("alice", PROJECT_ID),
    )
    assert result.success is True
    assert result.output["status"] == "queued"
    assert result.output["analysis_type"] == "inspect-managed-artifact"


@pytest.mark.asyncio
async def test_reverse_inspect_nimmt_keinen_upload_entgegen(client, alice):
    """Es gibt keinen Parameter, der einen Upload ausloest."""
    case_id = create_case(client, alice)
    schema = next(t for t in ALL_TOOLS if t.name == "reverse_inspect").schema
    assert "upload" not in " ".join(schema["properties"]).lower()
    assert "file_path" not in " ".join(schema["properties"]).lower()

    result = await tools.INSPECT_TOOL.execute(
        {"case_id": case_id, "analysis_type": "inspect-artifact"},
        ctx_for("alice", PROJECT_ID),
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_reverse_inspect_lehnt_fremden_fall_ab(client, alice, bob):
    case_id = create_case(client, bob, OTHER_PROJECT_ID)
    artifact_id = upload_artifact(client, bob, case_id)

    result = await tools.INSPECT_TOOL.execute(
        {"case_id": case_id, "artifact_id": artifact_id,
         "analysis_type": "inspect-managed-artifact"},
        ctx_for("alice", PROJECT_ID),
    )
    assert result.success is False
    assert result.error == "reverse_case_not_found"


@pytest.mark.asyncio
async def test_reverse_inspect_lehnt_unbekannten_analysetyp_ab(client, alice):
    case_id = create_case(client, alice)
    artifact_id = upload_artifact(client, alice, case_id)

    result = await tools.INSPECT_TOOL.execute(
        {"case_id": case_id, "artifact_id": artifact_id, "analysis_type": "rm -rf /"},
        ctx_for("alice", PROJECT_ID),
    )
    assert result.success is False
    assert result.error == "reverse_analysis_type_unknown"


@pytest.mark.asyncio
async def test_reverse_report_markiert_zielinhalte_als_nicht_vertrauenswuerdig(client, alice):
    case_id = create_case(client, alice)
    result = await tools.REPORT_TOOL.execute({"case_id": case_id},
                                             ctx_for("alice", PROJECT_ID))
    assert result.success is True
    assert result.output["untrusted_target_content"] is True
    assert "nicht vertrauenswuerdig" in result.output["untrusted_notice"]


@pytest.mark.asyncio
async def test_reverse_report_ist_begrenzt(client, alice):
    case_id = create_case(client, alice)
    result = await tools.REPORT_TOOL.execute({"case_id": case_id},
                                             ctx_for("alice", PROJECT_ID))
    assert len(result.output["observed"]) <= tools.MAX_LINES
    assert len(result.output["jobs"]) <= tools.MAX_LINES


@pytest.mark.asyncio
async def test_reverse_report_lehnt_fremden_fall_ab(client, alice, bob):
    case_id = create_case(client, bob, OTHER_PROJECT_ID)
    result = await tools.REPORT_TOOL.execute({"case_id": case_id},
                                             ctx_for("alice", PROJECT_ID))
    assert result.success is False
    assert result.error == "reverse_case_not_found"


@pytest.mark.asyncio
async def test_werkzeuge_tragen_einen_hinweis_auf_nicht_vertrauenswuerdigen_inhalt():
    hint = next(t for t in ALL_TOOLS if t.name == "reverse_cases").prompt_hint
    assert "nicht vertrauenswuerdig" in hint
