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


def _role_kw(model: str | None, template: str) -> dict:
    """Ohne eigenes Modell die Rolle (Agenten-Template, Kern E5) anfragen; älterer Kern ohne `template=` → wie früher."""
    from hydrahive.llm import client as _c
    return {} if model or not getattr(_c, "SUPPORTS_TEMPLATE", False) else {"template": template}


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
        return None  # ungültig/abgeschnitten – Aufrufer meldet das (nicht still „keine Vorschläge“)


_BATCH = 40          # Händler je KI-Aufruf: Antwort bleibt klein, nichts wird abgeschnitten
_MAX_TOKENS = 4096


def _build_prompt(groups: dict[str, dict], categories: list[sqlite3.Row], short: dict[str, str]) -> str:
    """Prompt mit KURZEN Händler-IDs (m1, m2 …): die KI muss keine langen Schlüssel zurückschreiben.

    Befund 20.11.2026 (Tills Sparkassen-Import, 66 Händler): Die KI sollte den vollen
    merchant_key (bis 180 Zeichen Rohtext) wiederholen; die Antwort brach bei
    max_tokens ab, das JSON war ungültig, es gab 0 Vorschläge ohne Meldung."""
    cat_lines = [f'{c["id"]}: {c["name"]} ({c["kind"]})' for c in categories if not c["archived"]]
    merchant_lines = [f'{short[gid]} :: {data["kind"]} :: {data["label"]}' for gid, data in groups.items()]
    return (
        "Verfügbare Kategorien (category_id: Name (Art)):\n"
        + "\n".join(cat_lines)
        + "\n\nHändler (id :: erwartete Art :: Beschreibung):\n"
        + "\n".join(merchant_lines)
        + '\n\nGib ein JSON-Array zurück. Jedes Element: '
        '{"id": "<id>", "category_id": <int>, "confidence": <0..1>}. '
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

    result: dict[int, tuple[int, float]] = {}
    keys = list(groups)
    for start in range(0, len(keys), _BATCH):
        part = {k: groups[k] for k in keys[start:start + _BATCH]}
        short = {gid: f"m{n}" for n, gid in enumerate(part, start + 1)}
        raw = await complete(
            [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": _build_prompt(part, categories, short)}],
            model=model,
            temperature=0.0,
            max_tokens=_MAX_TOKENS,
            **_role_kw(model, "modul-schnell"),
        )
        parsed = _parse(raw)
        if not isinstance(parsed, list):
            # Antwort unbrauchbar (z. B. abgeschnitten) – laut melden statt still 0 Vorschläge.
            raise ValueError("KI-Antwort war kein gültiges JSON-Array")
        by_short = {v: k for k, v in short.items()}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            ident = item.get("id", item.get("merchant_key"))
            group = part.get(by_short.get(ident, ident)) if isinstance(ident, str) else None
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
