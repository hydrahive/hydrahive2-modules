"""Per-user persistence for early Game Studio concept drafts."""

from __future__ import annotations

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

_MAX_DRAFTS_PER_USER = 100
_FIELDS = frozenset(
    {"title", "idea", "genre", "target_platform", "core_action", "success_condition", "current_step"}
)


class DraftConflict(ValueError):
    pass


def _row(value) -> dict | None:
    return dict(value) if value else None


def list_for(owner_user_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM module_game_studio_drafts
               WHERE owner_user_id = ? ORDER BY updated_at DESC, draft_id DESC""",
            (owner_user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get(owner_user_id: str, draft_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            """SELECT * FROM module_game_studio_drafts
               WHERE owner_user_id = ? AND draft_id = ?""",
            (owner_user_id, draft_id),
        ).fetchone()
    return _row(row)


def create(
    owner_user_id: str,
    *,
    entry_kind: str,
    title: str,
    idea: str,
    genre: str,
    target_platform: str,
) -> dict:
    timestamp = now_iso()
    draft_id = uuid7()
    with db(immediate=True) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM module_game_studio_drafts WHERE owner_user_id = ?",
            (owner_user_id,),
        ).fetchone()[0]
        if count >= _MAX_DRAFTS_PER_USER:
            raise DraftConflict("draft_limit_reached")
        conn.execute(
            """INSERT INTO module_game_studio_drafts
                   (draft_id, owner_user_id, entry_kind, title, idea, genre,
                    target_platform, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (draft_id, owner_user_id, entry_kind, title, idea, genre, target_platform, timestamp, timestamp),
        )
    created = get(owner_user_id, draft_id)
    if created is None:  # pragma: no cover - transaction invariant
        raise RuntimeError("created Game Studio draft could not be read back")
    return created


def update(owner_user_id: str, draft_id: str, revision: int, changes: dict[str, object]) -> dict | None:
    values = {key: value for key, value in changes.items() if key in _FIELDS and value is not None}
    if not values:
        return get(owner_user_id, draft_id)
    assignments = [f"{field} = ?" for field in values]
    assignments.extend(("revision = revision + 1", "updated_at = ?"))
    parameters = [*values.values(), now_iso(), owner_user_id, draft_id, revision]
    with db(immediate=True) as conn:
        result = conn.execute(
            f"""UPDATE module_game_studio_drafts SET {', '.join(assignments)}
                WHERE owner_user_id = ? AND draft_id = ? AND revision = ?""",
            parameters,
        )
        if result.rowcount == 0:
            exists = conn.execute(
                """SELECT revision FROM module_game_studio_drafts
                   WHERE owner_user_id = ? AND draft_id = ?""",
                (owner_user_id, draft_id),
            ).fetchone()
            if exists is not None:
                raise DraftConflict("draft_revision_conflict")
            return None
    return get(owner_user_id, draft_id)
