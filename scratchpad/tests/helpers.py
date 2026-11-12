"""Gemeinsame Konstanten und Helfer der Ideen-Tests."""
from __future__ import annotations

from pathlib import Path

MOD_PREFIX = "/api/modules/scratchpad"
PROJECT_A = "ideen-projekt-alice"
PROJECT_B = "ideen-projekt-bob"
TASKS_TABLE = "module_tasks"
TABLES = ("module_scratchpad_ideas", "module_scratchpad_idea_notes", TASKS_TABLE)
_MINIMAL_TASKS = (
    f"CREATE TABLE IF NOT EXISTS {TASKS_TABLE} (id TEXT PRIMARY KEY, username TEXT NOT NULL, project_id TEXT, "
    "session_id TEXT, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open', "
    "priority TEXT NOT NULL DEFAULT 'medium', created_at TEXT NOT NULL DEFAULT 'now', updated_at TEXT NOT NULL DEFAULT 'now')"
)


def ensure_tasks_table(module_dir: Path) -> None:
    """Tabelle des Tasks-Moduls anlegen: mit dessen echten Migrationen, wenn das Modul daneben liegt.

    So fällt ein geänderter Tabellenaufbau dort hier auf. Ohne Nachbarmodul reicht der bekannte Aufbau.
    """
    from hydrahive.db.connection import db
    from hydrahive.modules.migrations import apply_module_migrations

    migrations = module_dir.parent / "tasks" / "migrations"
    if migrations.is_dir():
        apply_module_migrations("tasks", migrations)
        return
    with db() as conn:
        conn.execute(_MINIMAL_TASKS)


def task_row(task_id: str) -> dict | None:
    from hydrahive.db.connection import db

    with db() as conn:
        row = conn.execute(f"SELECT * FROM {TASKS_TABLE} WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def make_ctx(username: str = "alice", project_id: str | None = None):
    from hydrahive.tools.base import ToolContext

    return ToolContext(
        session_id="sess-1", agent_id="agent-1", user_id=username,
        workspace=Path("/tmp"), project_id=project_id,
    )
