"""Brief-Vorlagen (Plan L3 Schritt 3, Spec §4.7). Gerüst aus der Fallakte; was nur der Mensch weiß, steht als
[Platzhalter] im Text. Fristen nur als Datum-Platzhalter, nie „binnen … Tagen“ (Prüfliste §4.7).

Normen: nur solche, deren Wortlaut am 20.10.2026 im Korpus gelesen wurde. Die Vorlagen behaupten nichts, was über
den Wortlaut hinausgeht (z. B. keine Minderungsquote, keine Zinshöhe) – das ist Sache des Agenten mit legal_norm bzw.
des Anwalts. Keine Rechtsberatung.
"""
from __future__ import annotations

from datetime import date
from typing import Any


class TemplateError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


_GREETING = "Sehr geehrte Damen und Herren,"
_CLOSING = "Mit freundlichen Grüßen\n\n\n[Unterschrift]\n{me_name}"

TEMPLATES: dict[str, dict[str, Any]] = {
    "mangelanzeige": {
        "label": "Mangelanzeige mit Fristsetzung (Miete)",
        "hint": "Mangel schriftlich anzeigen (§ 536c BGB) und eine Frist zur Beseitigung als Datum setzen.",
        "subject": "Mangelanzeige [Anschrift der Wohnung, Lage] – Aufforderung zur Mängelbeseitigung",
        "body": (
            "hiermit zeige ich Ihnen gemäß § 536c BGB folgenden Mangel der Mietsache an:\n\n"
            "[Beschreibung des Mangels: was, wo, seit wann, wie festgestellt]\n\n"
            "Nach § 535 BGB haben Sie die Mietsache während der Mietzeit in einem zum vertragsgemäßen Gebrauch geeigneten "
            "Zustand zu erhalten. Ich fordere Sie auf, den Mangel bis zum [Datum TT.MM.JJJJ] zu beseitigen.\n\n"
            "Auf § 536 BGB (Mietminderung bei Sach- und Rechtsmängeln) weise ich hin. Weitere Rechte behalte ich mir vor."
        ),
    },
    "mahnung": {
        "label": "Mahnung / Fristsetzung zur Zahlung oder Leistung",
        "hint": "Fällige Leistung anmahnen (§ 286 BGB) und ein Datum setzen.",
        "subject": "Mahnung – [Rechnung/Vertrag vom TT.MM.JJJJ]",
        "body": (
            "die folgende Leistung ist seit dem [Datum der Fälligkeit] fällig, aber bisher nicht erbracht:\n\n"
            "[Leistung bzw. Betrag, Rechnungs- oder Vertragsnummer]\n\n"
            "Ich fordere Sie hiermit auf, bis zum [Datum TT.MM.JJJJ] zu leisten. Dieses Schreiben ist eine Mahnung "
            "im Sinne von § 286 Abs. 1 BGB."
        ),
    },
    "widerspruch": {
        "label": "Widerspruch gegen einen Bescheid",
        "hint": "Widerspruch gegen einen Verwaltungsakt; Frist laut § 70 VwGO ein Monat nach Bekanntgabe – im "
                "Fristenrechner prüfen, Rechtsbehelfsbelehrung des Bescheids beachten.",
        "subject": "Widerspruch gegen den Bescheid vom [TT.MM.JJJJ], Az. [Aktenzeichen]",
        "body": (
            "gegen Ihren Bescheid vom [TT.MM.JJJJ], mir zugegangen am [TT.MM.JJJJ], lege ich hiermit Widerspruch ein "
            "(§§ 68, 70 VwGO).\n\n"
            "Begründung:\n[Begründung – oder: „Die Begründung reiche ich nach Akteneinsicht nach.“]\n\n"
            "Bitte bestätigen Sie mir den Eingang dieses Widerspruchs."
        ),
    },
    "kuendigung": {
        "label": "Kündigung (Vertrag)",
        "hint": "Kündigungsfrist und Form je Vertragsart prüfen (Wohnraum: § 573c, § 568 BGB – schriftlich).",
        "subject": "Kündigung [Vertrag, Vertragsnummer]",
        "body": (
            "hiermit kündige ich den [Vertrag, Vertragsnummer, Datum des Vertrags] fristgerecht zum [Datum TT.MM.JJJJ], "
            "hilfsweise zum nächstmöglichen Termin.\n\n"
            "[Bei Mietwohnung: Die Kündigung erfolgt schriftlich (§ 568 Abs. 1 BGB); Frist nach § 573c BGB.]\n\n"
            "Bitte bestätigen Sie mir den Eingang der Kündigung und das Beendigungsdatum schriftlich."
        ),
    },
    "akteneinsicht": {
        "label": "Bitte um Akteneinsicht",
        "hint": "Beteiligte haben ein Recht auf Akteneinsicht (Verwaltung § 29 VwVfG, Sozialverwaltung § 25 SGB X).",
        "subject": "Antrag auf Akteneinsicht, Az. [Aktenzeichen]",
        "body": (
            "in dem oben genannten Verfahren beantrage ich als Beteiligte/r Einsicht in die das Verfahren betreffenden "
            "Akten ([§ 29 VwVfG bzw. § 25 SGB X – passende Norm wählen]).\n\n"
            "Bitte teilen Sie mir mit, wann und wo ich die Akten einsehen kann, oder übersenden Sie mir Kopien. "
            "Ich bitte um Antwort bis zum [Datum TT.MM.JJJJ]."
        ),
    },
    "anwalt": {
        "label": "Anschreiben an den eigenen Anwalt",
        "hint": "Sachverhalt, Ziel und Fristen für die Erstberatung zusammenfassen.",
        "subject": "Bitte um Beratung – {title}",
        "body": (
            "ich bitte Sie um Beratung bzw. Vertretung in folgender Angelegenheit.\n\n"
            "Sachverhalt:\n{facts}\n\n"
            "Mein Ziel:\n{goal}\n\n"
            "Bekannte Fristen:\n[Fristen aus der Fallakte]\n\n"
            "Unterlagen füge ich bei bzw. reiche ich nach. Bitte teilen Sie mir mit, welche Unterlagen Sie benötigen "
            "und mit welchen Kosten ich für eine Erstberatung rechnen muss."
        ),
    },
}
ORDER = ("mangelanzeige", "mahnung", "widerspruch", "kuendigung", "akteneinsicht", "anwalt")


def list_templates() -> list[dict[str, str]]:
    return [{"key": k, "label": TEMPLATES[k]["label"], "hint": TEMPLATES[k]["hint"]} for k in ORDER]


def _address(p: dict[str, Any] | None, placeholder: str) -> str:
    if not p:
        return placeholder
    lines = [str(p.get("name") or "").strip()] + [ln.strip() for ln in str(p.get("address") or "").splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines) if len(lines) > 1 else (lines[0] + "\n[Anschrift]" if lines else placeholder)


def draft(key: str, *, case: dict[str, Any], parties: list[dict[str, Any]], recipient_id: int | None,
          today: date | None = None) -> dict[str, Any]:
    tpl = TEMPLATES.get(key)
    if tpl is None:
        raise TemplateError("template_unknown")
    me = next((p for p in parties if p.get("role") == "me"), None)
    recipient = None
    if recipient_id is not None:
        recipient = next((p for p in parties if p.get("id") == recipient_id), None)
        if recipient is None:
            raise TemplateError("recipient_not_in_case")
    fill = {"title": case.get("title") or "", "facts": case.get("facts") or "[Sachverhalt]",
            "goal": case.get("goal") or "[Ziel]", "me_name": (me or {}).get("name") or "[Name]"}
    body = "\n\n".join([_GREETING, tpl["body"].format(**fill), _CLOSING.format(**fill)])
    return {
        "letter_type": key,
        "sender": _address(me, "[Absender: Name und Anschrift – als Beteiligte/r „Ich / wir“ in der Fallakte eintragen]"),
        "recipient": _address(recipient, "[Empfänger: Name und Anschrift]"),
        "date": (today or date.today()).isoformat(),
        "their_ref": case.get("their_ref") or "",
        "our_ref": case.get("our_ref") or "",
        "subject": tpl["subject"].format(**fill),
        "body": body,
        "delivery": "einwurf_einschreiben",
        "attachments": [],
    }
