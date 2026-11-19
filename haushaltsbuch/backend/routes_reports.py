"""Endpunkte für die Auswertungen (Phase 1): Cashflow, Vermögen, Kategorien,
Budget-Verlauf, feste/variable Kosten.

Jeder Endpunkt liefert `json` (Default) oder `csv` (Query `format`). CSV
nutzt dieselben Zeilen wie `rows`, Semikolon getrennt, Beträge als
Minor-Units-Integer, mit CSV-Injection-Schutz für Textfelder. Ungültige
`range`-Werte liefern automatisch 422 (Literal-Validierung durch FastAPI).
"""

from __future__ import annotations

import csv
import io
from typing import Literal

from fastapi import APIRouter, Response

from . import reports
from .access import Principal

router = APIRouter(prefix="/reports")

RangeParam = Literal["3", "6", "12", "24", "all"]
FormatParam = Literal["json", "csv"]

_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@")


def _sanitize_csv_value(value) -> object:
    """Schützt Textfelder vor CSV-Injection (Excel/LibreOffice-Formeln).

    Werte, die mit `= + - @` beginnen, werden mit einem `'` präfixt, damit
    Tabellenkalkulationen sie nicht als Formel interpretieren. Zahlen und
    Booleans bleiben unverändert.
    """
    if isinstance(value, str) and value.startswith(_CSV_INJECTION_PREFIXES):
        return f"'{value}"
    return value


def _csv_response(report_name: str, range_param: str, rows: list[dict]) -> Response:
    buffer = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _sanitize_csv_value(value) for key, value in row.items()})
    filename = f"haushaltsbuch-{report_name}-{range_param}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cashflow")
def get_cashflow(
    principal: Principal, range: RangeParam = "12", format: FormatParam = "json"
):
    data = reports.cashflow(principal, range)
    if format == "csv":
        return _csv_response("cashflow", range, data["rows"])
    return data


@router.get("/net-worth")
def get_net_worth(
    principal: Principal, range: RangeParam = "12", format: FormatParam = "json"
):
    data = reports.net_worth(principal, range)
    if format == "csv":
        return _csv_response("net-worth", range, data["rows"])
    return data


@router.get("/categories")
def get_categories(
    principal: Principal,
    range: RangeParam = "12",
    format: FormatParam = "json",
    parent_id: int | None = None,
):
    data = reports.categories(principal, range, parent_id)
    if format == "csv":
        return _csv_response("categories", range, data["rows"])
    return data


@router.get("/budgets")
def get_budgets_report(
    principal: Principal, range: RangeParam = "12", format: FormatParam = "json"
):
    data = reports.budgets(principal, range)
    if format == "csv":
        return _csv_response("budgets", range, data["rows"])
    return data


@router.get("/fixed-costs")
def get_fixed_costs(
    principal: Principal, range: RangeParam = "12", format: FormatParam = "json"
):
    data = reports.fixed_costs(principal, range)
    if format == "csv":
        return _csv_response("fixed-costs", range, data["rows"])
    return data
