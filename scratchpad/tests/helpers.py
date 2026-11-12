"""Gemeinsame Konstanten und Helfer der Ideen-Tests."""
from __future__ import annotations

from pathlib import Path

MOD_PREFIX = "/api/modules/scratchpad"
PROJECT_A = "ideen-projekt-alice"
PROJECT_B = "ideen-projekt-bob"
TASKS_TABLE = "module_tasks"
BOARDS_TABLE = "module_blueprint_boards"
TABLES = ("module_scratchpad_ideas", "module_scratchpad_idea_notes", TASKS_TABLE, BOARDS_TABLE)
OLD_BOARDS_TABLE = "module_blueprint_boards_ohne_projekt"
_OLD_BOARD_COLUMNS = (
    """(id INTEGER PRIMARY KEY AUTOINCREMENT, "user" TEXT NOT NULL, name TEXT NOT NULL DEFAULT 'Neues Board', """
    """graph_json TEXT NOT NULL DEFAULT '{"nodes":[],"edges":[]}', """
    "created_at TEXT NOT NULL DEFAULT 'now', updated_at TEXT NOT NULL DEFAULT 'now')"
)
_NEW_BOARD_COLUMNS = _OLD_BOARD_COLUMNS[:-1] + ", project_id TEXT, proposal_json TEXT)"
OLD_TASKS_TABLE = "module_tasks_ohne_herkunft"
_MINIMAL_COLUMNS = (
    "(id TEXT PRIMARY KEY, username TEXT NOT NULL, project_id TEXT, "
    "session_id TEXT, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open', "
    "priority TEXT NOT NULL DEFAULT 'medium', created_at TEXT NOT NULL DEFAULT 'now', updated_at TEXT NOT NULL DEFAULT 'now')"
)
_MINIMAL_TASKS = f"CREATE TABLE IF NOT EXISTS {TASKS_TABLE} {_MINIMAL_COLUMNS}"


def ensure_old_tasks_table() -> str:
    """Tabelle im Aufbau des Tasks-Moduls bis 1.2.1, ohne die Spalten für die Herkunft."""
    from hydrahive.db.connection import db

    with db() as conn:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {OLD_TASKS_TABLE} {_MINIMAL_COLUMNS}")
    return OLD_TASKS_TABLE


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


def ensure_boards_table(module_dir: Path) -> None:
    """Tabelle des Blueprint-Moduls anlegen: mit dessen echten Migrationen, wenn das Modul daneben liegt."""
    from hydrahive.db.connection import db
    from hydrahive.modules.migrations import apply_module_migrations

    migrations = module_dir.parent / "blueprint" / "migrations"
    if migrations.is_dir():
        apply_module_migrations("blueprint", migrations)
        return
    with db() as conn:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {BOARDS_TABLE} {_NEW_BOARD_COLUMNS}")


def ensure_old_boards_table() -> str:
    """Tabelle im Aufbau des Blueprint-Moduls bis 1.2.1, ohne Projekt und Vorschlag."""
    from hydrahive.db.connection import db

    with db() as conn:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {OLD_BOARDS_TABLE} {_OLD_BOARD_COLUMNS}")
    return OLD_BOARDS_TABLE


def board_row(board_id: int, table: str = BOARDS_TABLE) -> dict | None:
    from hydrahive.db.connection import db

    with db() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (board_id,)).fetchone()
    return dict(row) if row else None


def task_row(task_id: str, table: str = TASKS_TABLE) -> dict | None:
    from hydrahive.db.connection import db

    with db() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def make_ctx(username: str = "alice", project_id: str | None = None):
    from hydrahive.tools.base import ToolContext

    return ToolContext(
        session_id="sess-1", agent_id="agent-1", user_id=username,
        workspace=Path("/tmp"), project_id=project_id,
    )
