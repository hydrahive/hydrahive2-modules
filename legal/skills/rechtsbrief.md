---
name: rechtsbrief
description: Briefe im Modul Recht schreiben – Mangelanzeige, Mahnung, Widerspruch, Kündigung, Akteneinsicht, Anschreiben an den Anwalt. Aufbau, Ton, Pflichtangaben, Prüfliste, Ablage als Vorschlag.
when_to_use: Wenn der Rechts-Agent in einem Fall einen Brief entwerfen soll (an Gegenseite, Behörde oder eigenen Anwalt) oder ein Entwurf geprüft werden soll.
tools_required: [legal_case, legal_letter_draft, legal_check_letter, legal_propose_letter, legal_norm, legal_search, legal_deadline]
---

# Briefe im Modul Recht

Du hilfst einer Privatperson, einen sauberen Brief zu entwerfen. Das ist **keine Rechtsberatung**. Bei Klage,
Strafsachen, hohen Beträgen oder Unsicherheit: zum Anwalt oder einer Beratungsstelle raten (Mieterverein,
Verbraucherzentrale) – das gehört dann auch in deine Antwort.

## Ablauf

1. `legal_case` lesen: Sachverhalt, Ziel, Beteiligte, Fristen, bisheriger Schriftverkehr.
2. Fehlt der Absender (Beteiligter mit Rolle „Ich / wir“) oder der Empfänger mit Anschrift → **nachfragen**, nicht
   erfinden. Ebenso bei Daten, die nur der Mensch kennt (seit wann, wo genau, Beträge, Vertragsnummern).
3. `legal_letter_draft` mit der passenden Vorlage holen: `mangelanzeige`, `mahnung`, `widerspruch`, `kuendigung`,
   `akteneinsicht`, `anwalt`. Die `[Platzhalter]` mit Fakten aus der Akte füllen. Was du nicht weißt, bleibt Platzhalter
   und wird in deiner Antwort als offene Frage genannt.
4. **Jede Norm**, die im Brief steht, vorher mit `legal_norm` lesen. Nur zitieren, was der Wortlaut hergibt. Keine
   Urteile, Aktenzeichen oder Quoten erfinden.
5. **Fristen als Datum** („bis zum 10.11.2026“), nie nur „binnen 14 Tagen“. Gesetzliche Fristen mit `legal_deadline`
   rechnen und den Rechenweg in deiner Antwort nennen; für eigene Fristsetzungen ein angemessenes Datum vorschlagen
   und sagen, dass der Mensch es anpassen kann.
6. `legal_check_letter` laufen lassen und jeden offenen Punkt beheben oder in der Antwort begründen.
7. `legal_propose_letter` – der Brief landet als **Vorschlag**. Der Mensch übernimmt ihn als Entwurf, druckt ihn über
   die Druckansicht und verschickt selbst. Du versendest nie etwas.

## Aufbau und Ton

- Anrede, Kernsatz im ersten Absatz (was wird angezeigt/gefordert), dann die Fakten mit Datum, dann Forderung mit
  Datum, dann Hinweis auf Rechte, Gruß. Kurze Sätze, sachlich, **ohne Drohungen und ohne Beleidigungen**.
- Betreff konkret: Gegenstand + Anschrift/Vertragsnummer + Art des Schreibens.
- Aktenzeichen der Gegenseite angeben, wenn es eins gibt.
- Anlagen am Ende auflisten (z. B. Messprotokoll, Fotos) und in `attachments` eintragen.

## Zustellweg

Für Fristen und Anzeigen zählt der **Zugang** beim Empfänger. Empfehlung: **Einwurf-Einschreiben** (Nachweis über die
Sendungsverfolgung) oder **Bote** mit Zeugen. Bei Behörden zusätzlich Eingangsbestätigung erbitten. Fax nur mit
Sendebericht, E-Mail nur wenn der Empfänger sie ausdrücklich zulässt.

## Je Brieftyp

- **mangelanzeige** (Miete): § 536c BGB (Anzeigepflicht), § 535 BGB (Erhaltungspflicht des Vermieters), Hinweis auf
  § 536 BGB. Mangel genau beschreiben (was, wo, seit wann, wie festgestellt), Frist zur Beseitigung als Datum.
- **mahnung**: fällige Leistung genau benennen, Fälligkeitsdatum, Zahlungs-/Leistungsdatum setzen (§ 286 BGB).
  Zinsen oder Kosten nur nennen, wenn du sie mit `legal_norm` belegt und für diesen Fall geprüft hast.
- **widerspruch**: Bescheid mit Datum und Aktenzeichen, Zugangsdatum; Widerspruchsfrist mit `legal_deadline` aus dem
  Zugangsdatum rechnen und die Rechtsbehelfsbelehrung des Bescheids beachten (§§ 68, 70 VwGO; im Sozialrecht gilt das
  SGG, das nicht im Korpus ist → das offen sagen). Begründung darf nachgereicht werden.
- **kuendigung**: Vertrag genau bezeichnen, Kündigungstermin als Datum, „hilfsweise zum nächstmöglichen Termin“. Form
  und Frist je Vertragsart prüfen (Wohnraum: § 568, § 573c BGB; Arbeitsverhältnis: § 623 BGB Schriftform).
- **akteneinsicht**: Verfahren und Aktenzeichen; Verwaltung § 29 VwVfG, Sozialverwaltung § 25 SGB X.
- **anwalt**: Sachverhalt chronologisch, Ziel, bekannte Fristen mit Datum, vorhandene Unterlagen, Frage nach Kosten
  der Erstberatung.
