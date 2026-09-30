"""Task-ID auflösen: volle UUID oder eindeutiger Anfang (Kurz-ID).

Gemeinsam für task_read, task_write und task_delete (Task d61ae32b).
Vorher konnte task_write nur volle UUIDs, und eine leere ID passte per
startswith("") auf jeden Task: task_delete mit leerer ID löschte den
einzigen Task eines Nutzers.
"""
from __future__ import annotations

from typing import Any

from .. import service


def resolve(username: str, task_id: str | None) -> tuple[dict[str, Any] | None, str | None]:
    """Gibt (task, None) oder (None, Fehlertext) zurück. Nur Tasks des Nutzers."""
    tid = (task_id or "").strip()
    if not tid:
        return None, "Keine Task-ID angegeben."
    task = service.get_task(username, tid)
    if task is not None:
        return task, None
    matches = [t for t in service.list_tasks(username) if t["id"].startswith(tid)]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        ids = ", ".join(t["id"][:8] for t in matches)
        return None, f"Mehrdeutig — {len(matches)} Tasks beginnen mit '{tid}': {ids}"
    return None, f"Task '{tid}' nicht gefunden."
