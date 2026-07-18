"""Kategorie-Vorschläge aus der Buchungshistorie (kostenlos, deterministisch).

Idee: Wurde ein Händler früher schon gebucht, schlagen wir dieselbe Kategorie
erneut vor. Das löst den Massenimport für alle Stammhändler ohne LLM-Kosten.
"""
from __future__ import annotations

import sqlite3

_STRONG = 0.95
_WEAK = 0.7


def merchant_key(counterparty_identifier: str | None, counterparty: str | None) -> tuple[str, str] | None:
    """Match-Schlüssel für einen Händler: (art, wert) oder None.

    Bevorzugt die (maskierte) Gegenkonto-Kennung; fällt sonst auf den
    normalisierten Namen zurück.
    """
    if counterparty_identifier:
        return ("id", counterparty_identifier.strip().casefold())
    if counterparty:
        normalized = " ".join(counterparty.split()).casefold()
        if normalized:
            return ("name", normalized)
    return None


def _history_index(conn: sqlite3.Connection, household_id: int) -> dict[tuple[str, str], list[tuple[int, str, int]]]:
    """Baut aus gebuchten Transaktionen einen Index Händler → Kategorie-Treffer.

    Wert je Händler: Liste von (category_id, kind, count), damit der Aufrufer die
    für das Vorzeichen passende und häufigste Kategorie wählen kann.
    """
    rows = conn.execute(
        "SELECT t.counterparty AS counterparty, "
        "       ci.counterparty_identifier AS counterparty_identifier, "
        "       p.category_id AS category_id, c.kind AS kind, COUNT(*) AS hits "
        "FROM module_haushaltsbuch_transactions t "
        "JOIN module_haushaltsbuch_postings p "
        "  ON p.transaction_id = t.id AND p.household_id = t.household_id "
        "JOIN module_haushaltsbuch_categories c "
        "  ON c.id = p.category_id AND c.household_id = t.household_id "
        "LEFT JOIN module_haushaltsbuch_import_rows ci "
        "  ON ci.transaction_id = t.id AND ci.household_id = t.household_id "
        "WHERE t.household_id = ? AND t.status = 'posted' "
        "  AND p.category_id IS NOT NULL AND c.archived = 0 "
        "GROUP BY t.counterparty, ci.counterparty_identifier, p.category_id, c.kind",
        (household_id,),
    ).fetchall()
    index: dict[tuple[str, str], list[tuple[int, str, int]]] = {}
    for row in rows:
        key = merchant_key(row["counterparty_identifier"], row["counterparty"])
        if key is None:
            continue
        index.setdefault(key, []).append((row["category_id"], row["kind"], row["hits"]))
    return index


def suggest(
    conn: sqlite3.Connection, household_id: int, rows: list[sqlite3.Row]
) -> dict[int, tuple[int, float]]:
    """Vorschläge aus der Historie: row_id → (category_id, confidence).

    Nur Zeilen mit gültigem Betrag werden bedient (Vorzeichen bestimmt income/expense).
    Zeilen ohne Treffer bleiben unberücksichtigt (kommen später ggf. ans LLM).
    """
    index = _history_index(conn, household_id)
    result: dict[int, tuple[int, float]] = {}
    for row in rows:
        amount = row["amount_minor"]
        if amount is None or amount == 0:
            continue
        key = merchant_key(row["counterparty_identifier"], row["counterparty"])
        if key is None:
            continue
        candidates = index.get(key)
        if not candidates:
            continue
        wanted_kind = "income" if amount > 0 else "expense"
        matching = [item for item in candidates if item[1] == wanted_kind]
        if not matching:
            continue
        category_id = max(matching, key=lambda item: item[2])[0]
        confidence = _STRONG if key[0] == "id" else _WEAK
        result[row["id"]] = (category_id, confidence)
    return result
