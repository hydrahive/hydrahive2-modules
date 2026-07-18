"""Hybrid-Orchestrierung der Auto-Kategorisierung.

Ablauf von suggest_categories:
  1. Draft-Batch prüfen, offene Zeilen (ohne category_id, ohne Vorschlag) laden.
  2. Historie-Lookup (kostenlos) — deckt Stammhändler ab.
  3. Rest per LLM-Batch (ein Call, dedupliziert nach Händler).
  4. Vorschläge persistieren (suggested_category_id/source/confidence).

accept_suggestions übernimmt Vorschläge in category_id + status='accepted' —
erst dann greift der bestehende complete-Flow. Nichts wird automatisch gebucht.
"""
from __future__ import annotations

import sqlite3

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit, categorize_history, categorize_llm
from .access import conflict, membership, require_row
from .common import NOW
from .import_persistence import _batch_dict


def _require_draft(conn: sqlite3.Connection, batch_id: int, household_id: int) -> sqlite3.Row:
    batch = require_row(
        conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_batches WHERE id=? AND household_id=?",
            (batch_id, household_id),
        ).fetchone(),
        "import_batch_not_found",
    )
    if batch["status"] != "draft":
        conflict("import_batch_not_draft")
    return batch


async def suggest_categories(
    batch_id: int, principal: AuthPrincipal, *, model: str | None = None
) -> dict:
    # 1) Lesen: offene Zeilen + Kategorien (Transaktion NICHT über das await halten).
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        _require_draft(conn, batch_id, household_id)
        open_rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_rows "
            "WHERE batch_id=? AND household_id=? AND category_id IS NULL "
            "AND suggested_category_id IS NULL AND status IN ('pending','duplicate') "
            "ORDER BY id",
            (batch_id, household_id),
        ).fetchall()
        categories = conn.execute(
            "SELECT id,name,kind,archived FROM module_haushaltsbuch_categories "
            "WHERE household_id=? AND archived=0 ORDER BY id",
            (household_id,),
        ).fetchall()
        history = categorize_history.suggest(conn, household_id, open_rows)

    # 2) LLM nur für Zeilen ohne Historie-Treffer (ein Batch-Call, async).
    remaining = [row for row in open_rows if row["id"] not in history]
    llm: dict[int, tuple[int, float]] = {}
    if remaining and categories:
        llm = await categorize_llm.suggest(remaining, categories, model=model)

    # 3) Schreiben: Vorschläge persistieren (nur solange Batch noch Draft ist).
    suggestions: dict[int, tuple[int, float, str]] = {}
    for row_id, (category_id, confidence) in history.items():
        suggestions[row_id] = (category_id, confidence, "history")
    for row_id, (category_id, confidence) in llm.items():
        suggestions.setdefault(row_id, (category_id, confidence, "llm"))

    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        _require_draft(conn, batch_id, household_id)
        applied = 0
        for row_id, (category_id, confidence, source) in suggestions.items():
            cursor = conn.execute(
                f"UPDATE module_haushaltsbuch_import_rows "
                f"SET suggested_category_id=?,suggestion_source=?,suggestion_confidence=?,"
                f"updated_at={NOW} "
                "WHERE id=? AND household_id=? AND batch_id=? AND category_id IS NULL "
                "AND status IN ('pending','duplicate')",
                (category_id, source, confidence, row_id, household_id, batch_id),
            )
            applied += cursor.rowcount
        audit.record(
            conn, household_id, principal.user_id, "import_batch", batch_id,
            "suggest_categories",
            after={
                "suggested": applied,
                "from_history": len(history),
                "from_llm": len(llm),
                "model": model,
            },
        )
        batch = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_batches WHERE id=?", (batch_id,)
        ).fetchone()
        result = _batch_dict(conn, batch, True)
    return result


def accept_suggestions(
    batch_id: int,
    revision: int,
    row_ids: list[int] | None,
    principal: AuthPrincipal,
) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        batch = _require_draft(conn, batch_id, household_id)
        if batch["revision"] != revision:
            conflict("import_batch_already_changed")

        query = (
            "SELECT r.*, c.kind AS suggested_kind "
            "FROM module_haushaltsbuch_import_rows r "
            "JOIN module_haushaltsbuch_categories c "
            "  ON c.id = r.suggested_category_id AND c.household_id = r.household_id "
            "WHERE r.batch_id=? AND r.household_id=? AND r.suggested_category_id IS NOT NULL "
            "AND r.category_id IS NULL AND r.status IN ('pending','duplicate') "
            "AND c.archived=0"
        )
        params: list = [batch_id, household_id]
        if row_ids is not None:
            if not row_ids:
                raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_rows_selected")
            placeholders = ",".join("?" for _ in row_ids)
            query += f" AND r.id IN ({placeholders})"
            params.extend(row_ids)
        rows = conn.execute(query, params).fetchall()

        applied = 0
        for row in rows:
            amount = row["amount_minor"]
            if amount is None or amount == 0:
                continue
            expected_kind = "income" if amount > 0 else "expense"
            if row["suggested_kind"] != expected_kind:
                continue
            if row["errors_json"] and row["errors_json"] != "[]":
                continue
            cursor = conn.execute(
                f"UPDATE module_haushaltsbuch_import_rows "
                f"SET category_id=suggested_category_id,status='accepted',"
                f"revision=revision+1,updated_at={NOW} "
                "WHERE id=? AND household_id=? AND revision=?",
                (row["id"], household_id, row["revision"]),
            )
            applied += cursor.rowcount
        audit.record(
            conn, household_id, principal.user_id, "import_batch", batch_id,
            "accept_suggestions", after={"accepted": applied},
        )
        result = _batch_dict(
            conn,
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_import_batches WHERE id=?", (batch_id,)
            ).fetchone(),
            True,
        )
    return result
