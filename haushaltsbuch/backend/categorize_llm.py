"""LLM-gestützte Kategorie-Vorschläge für unbekannte Händler.

Kernidee gegen Kosten/Latenz: Hunderte Buchungen enthalten meist nur wenige
Dutzend einzigartige Händler. Wir deduplizieren auf Händler-Ebene und schicken
EINEN Batch-Call ans konfigurierte Modell (lokal via Ollama/LM-Studio oder Cloud).
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3

from hydrahive.llm.client import complete

from .categorize_history import merchant_key

logger = logging.getLogger(__name__)

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

_SYSTEM = (
    "Du bist ein Buchhaltungs-Assistent für ein privates Haushaltsbuch. "
    "Ordne jedem Händler genau eine der vorgegebenen Kategorien zu. "
    "Nutze ausschließlich die vorgegebenen category_id-Werte. "
    "Antworte NUR mit einem JSON-Array, ohne Erklärtext."
)


def _merchant_label(row: sqlite3.Row) -> str:
    parts = [row["counterparty"] or "", row["purpose"] or ""]
    return " – ".join(part for part in parts if part).strip()[:180]


def _group_merchants(rows: list[sqlite3.Row]) -> dict[str, dict]:
    """Dedupliziert Zeilen zu Händler-Gruppen.

    Rückgabe: merchant_key_str → {label, kind, row_ids}. `kind` ergibt sich aus
    dem Vorzeichen des Betrags (gemischte Vorzeichen → getrennt behandelt).
    """
    groups: dict[str, dict] = {}
    for row in rows:
        amount = row["amount_minor"]
        if amount is None or amount == 0:
            continue
        key = merchant_key(row["counterparty_identifier"], row["counterparty"])
        label = _merchant_label(row)
        if key is None:
            if not label:
                continue
            key = ("name", label.casefold())
        kind = "income" if amount > 0 else "expense"
        group_key = f"{kind}|{key[0]}|{key[1]}"
        entry = groups.setdefault(
            group_key, {"label": label or key[1], "kind": kind, "row_ids": []}
        )
        entry["row_ids"].append(row["id"])
    return groups


def _parse(text: str):
    text = _THINK.sub("", text or "").strip()
    fence = _FENCE.search(text)
    if fence:
        text = fence.group(1)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return []


def _build_prompt(groups: dict[str, dict], categories: list[sqlite3.Row]) -> str:
    cat_lines = [
        f'{c["id"]}: {c["name"]} ({c["kind"]})'
        for c in categories
        if not c["archived"]
    ]
    merchant_lines = [
        f'{gid} :: {data["kind"]} :: {data["label"]}'
        for gid, data in groups.items()
    ]
    return (
        "Verfügbare Kategorien (category_id: Name (Art)):\n"
        + "\n".join(cat_lines)
        + "\n\nHändler (merchant_key :: erwartete Art :: Beschreibung):\n"
        + "\n".join(merchant_lines)
        + '\n\nGib ein JSON-Array zurück. Jedes Element: '
        '{"merchant_key": "<merchant_key>", "category_id": <int>, "confidence": <0..1>}. '
        "Wähle nur category_id-Werte, deren Art zur erwarteten Art des Händlers passt. "
        "Wenn unsicher, wähle die plausibelste Kategorie mit niedrigerer confidence."
    )


async def suggest(
    rows: list[sqlite3.Row],
    categories: list[sqlite3.Row],
    *,
    model: str | None = None,
) -> dict[int, tuple[int, float]]:
    """Vorschläge vom LLM: row_id → (category_id, confidence).

    Nur Zeilen ohne bestehenden Vorschlag übergeben. Halluzinierte/kind-fremde
    category_id-Werte werden verworfen (leiser Skip, kein Crash).
    """
    groups = _group_merchants(rows)
    if not groups:
        return {}
    valid_by_kind: dict[str, set[int]] = {"income": set(), "expense": set()}
    for cat in categories:
        if not cat["archived"]:
            valid_by_kind[cat["kind"]].add(cat["id"])

    prompt = _build_prompt(groups, categories)
    raw = await complete(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}],
        model=model,
        temperature=0.0,
        max_tokens=2048,
    )
    parsed = _parse(raw)
    if not isinstance(parsed, list):
        return {}

    result: dict[int, tuple[int, float]] = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        group_key = item.get("merchant_key")
        group = groups.get(group_key) if isinstance(group_key, str) else None
        category_id = item.get("category_id")
        if group is None or not isinstance(category_id, int):
            continue
        if category_id not in valid_by_kind.get(group["kind"], set()):
            continue
        confidence = item.get("confidence")
        confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.5
        confidence = min(max(confidence, 0.0), 1.0)
        for row_id in group["row_ids"]:
            result[row_id] = (category_id, confidence)
    return result
