"""Kleine, feste Incus-Schnittstelle für Vibe (Kopie aus hydralabor, PLAN-V1.md Entscheidung 1). Keine Shell."""
from __future__ import annotations

from hydrahive.containers import incus_client


def available() -> bool:
    return incus_client.is_available()


async def run(*args: str, timeout: float = 60.0, input_bytes: bytes | None = None) -> tuple[int, str, str]:
    return await incus_client._run(*args, timeout=timeout, input_bytes=input_bytes)


def first_column(csv_out: str) -> set[str]:
    """Namen aus `incus … list --format csv` (erste Spalte). incus 6.0.0 kennt bei network/acl/snapshot kein -c."""
    return {line.split(",", 1)[0].strip() for line in csv_out.splitlines() if line.strip()}


async def run_to_file(
    *args: str, out_path, timeout: float = 900.0, max_bytes: int = 16 << 30
) -> tuple[int, str]:
    """`incus …` mit der Standardausgabe BYTEGENAU in eine Datei (kein Text, kein Speicher). Die Dateigröße ist hart
    begrenzt (RLIMIT_FSIZE: der Prozess wird beim Überschreiten beendet), das Zeitlimit beendet den Prozess."""
    import asyncio
    import resource

    from hydrahive.containers.incus_client import IncusError

    if not incus_client.is_available():
        raise IncusError("incus_missing")

    def _limit() -> None:
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_bytes, max_bytes))

    handle = await asyncio.to_thread(open, out_path, "wb")
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            "incus", *args,
            stdin=asyncio.subprocess.DEVNULL, stdout=handle, stderr=asyncio.subprocess.PIPE,
            preexec_fn=_limit,
        )
        try:
            _, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            raise IncusError("incus_timeout") from None
    finally:
        # Bei Timeout, Abbruch des Tasks (CancelledError) und jedem anderen Fehler läuft der Kindprozess nicht weiter.
        if proc is not None and proc.returncode is None:
            proc.kill()
            await asyncio.shield(proc.wait())
        handle.close()
    return proc.returncode or 0, err.decode(errors="replace")
