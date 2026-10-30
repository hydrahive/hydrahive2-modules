"""Aufträge des Labors (PLAN-L1.md „Assistent“ / „Labor-Seite“): anlegen, entfernen, zurücksetzen, Netz prüfen,
Testlauf. Höchstens einer gleichzeitig (state.begin). Der Fortschritt landet im Zustand; die Seite fragt ihn ab.

Aufräumen bei Fehlern und „Labor entfernen“ löschen nur, was laut Zustand von diesem Modul angelegt wurde.
"""
from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable

from . import container, lab_project, network, provision, state
from .container import Limits

logger = logging.getLogger(__name__)
Report = Callable[[str], None]
_SUMMARY = re.compile(r"^=*\s*(?=.*\bin [\d.]+s)(.*(?:passed|failed|error).*?)\s*=*$", re.MULTILINE)
_FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+)", re.MULTILINE)
_TEST_CMD = "cd /work/hydrahive2 && pytest -q -n 2 -p no:cacheprovider core/tests 2>&1 | tail -n 80"
_tasks: set[asyncio.Task] = set()


async def create(report: Report) -> None:
    st = state.get()
    made = st["made"]
    report("network")
    net = await network.ensure_network()
    if net.subnet:
        state.mark_made("network")
    try:
        report("container")
        if "container" not in made:
            await container.launch_and_probe(Limits(cpu=st["cpu"], ram_mb=st["ram_mb"], disk_gb=st["disk_gb"]))
            state.mark_made("container")
        if "setup" not in made:
            await provision.setup(report)
            state.mark_made("setup")
        report("snapshot")
        await provision.snapshot()
        state.mark_made("snapshot")
    except Exception:
        await _undo_partial()
        raise
    report("project")
    if "project" not in made:
        out = lab_project.create(admin=st["admin"], model=st["model"])
        state.mark_made("project", **out)
    state.net_ok()
    state.set_step("ready")


async def _undo_partial() -> None:
    """Halbes Labor wieder weg – nur Teile, die laut Zustand von uns sind."""
    made = state.get()["made"]
    if "container" in made or "setup" in made or "snapshot" in made:
        await container.remove()
        state.unmark("container", "setup", "snapshot")
    if "network" in made:
        await network.remove()
        state.unmark("network")


async def remove(report: Report) -> None:
    made = state.get()["made"]
    if "project" in made:
        report("project")
        lab_project.remove(made)
    if "container" in made:
        report("container")
        await container.remove()
    if "network" in made:
        report("network")
        await network.remove()
    state.clear()


async def reset(report: Report) -> None:
    report("reset")
    await provision.reset()
    state.net_ok()


async def probe(report: Report) -> None:
    report("probe")
    await network.sync_rules()
    try:
        await container.wait_for_address()
        await network.probe(container.NAME, await network.gateway())
    except network.LaborNetworkError:
        await container.stop()                                    # Sperre offen → Labor aus, bis geklärt
        raise
    state.net_ok()


def parse_test(rc: int, out: str) -> dict:
    m = _SUMMARY.findall(out)
    summary = m[-1].strip() if m else ""
    num = lambda w: int(x.group(1)) if (x := re.search(rf"(\d+) {w}", summary)) else 0
    failures = _FAILED.findall(out)[:20]
    return {"ok": rc == 0 and bool(summary) and num("failed") == 0, "summary": summary, "passed": num("passed"),
            "failed": num("failed"), "failures": failures}


async def test(report: Report) -> None:
    report("test")
    rc, out, _ = await container.incus.run(
        "exec", container.NAME, "--cwd", "/work", "--user", "1000", "--group", "1000", "--env", "HOME=/home/labor",
        "--", "bash", "-c", _TEST_CMD, timeout=1800)
    state.set_test(parse_test(rc, out))


JOBS: dict[str, Callable[[Report], Awaitable[None]]] = {
    "create": create, "remove": remove, "reset": reset, "probe": probe, "test": test}


async def _run(name: str) -> None:
    code, step = "", ""
    try:
        await JOBS[name](state.progress)
    except provision.SetupError as e:
        code, step = e.code, e.step
    except (container.LaborError, network.LaborNetworkError) as e:
        code = e.code
    except Exception:
        logger.exception("Hydra-Labor: Auftrag %s gescheitert", name)
        code = "labor_failed"
    state.finish(error_code=code, error_step=step)


def start(name: str) -> bool:
    """Auftrag im Hintergrund starten. False, wenn schon einer läuft."""
    if name not in JOBS:
        raise KeyError(name)
    if not state.begin(name):
        return False
    task = asyncio.get_running_loop().create_task(_run(name))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return True
