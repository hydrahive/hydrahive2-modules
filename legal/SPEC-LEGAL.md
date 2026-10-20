# Modul „Recht“ (`legal`) – Rechtsrecherche mit Beleg, Fallakte und Briefe

Stand: 20.10.2026 · Task f0b8d254 · Status: **freigegeben (Till, 20.10.)**, L0 gemessen (§ 6a) · Datei: `legal/SPEC-LEGAL.md`

## 1. Ziel

Till und seine Familie bekommen ein Werkzeug für **eigene** Rechtsangelegenheiten wie Mietsache, Versicherung
oder Behörde:

1. **Rechtsauskunft mit Beleg:** Jede Rechtsaussage stützt sich auf eine Norm, die wörtlich und mit Stand
   nachgewiesen ist. Erfundene Paragrafen werden mechanisch erkannt.
2. **Fallakte:** Sachverhalt, Beteiligte, Fristen und Schriftverkehr an einem Ort, hinter der Vault-PIN.
3. **Briefe:** Vorschläge für rechtlich saubere Schreiben an Gegenseite und Anwalt, mit Prüfliste, als PDF.

Das Modul ersetzt keinen Anwalt und keinen Mieterschutzbund. Es bereitet vor, damit man dort gut ankommt.

## 2. Entscheidungen (Till, 20.10.2026)

- Die Familie nutzt es mit, nicht nur Till.
- **Ein Projekt pro Fall.** Der Agent im Projekt arbeitet mit dem Modul. Wer im Projekt Mitglied ist, sieht den Fall.
- Eigener Menüpunkt **„Recht“** für Aufnahme und Ausgabe der Fälle.
- Nur kostenlose Quellen, keine laufenden Kosten.

## 3. Rechtlicher Rahmen (Wortlaut geprüft 20.10., keine Rechtsberatung)

| Norm | Inhalt | Folge fürs Modul |
|---|---|---|
| § 5 Abs. 1 UrhG | Gesetze, Verordnungen und Entscheidungen haben keinen urheberrechtlichen Schutz | Gesetzestexte dürfen geladen und gespeichert werden |
| gesetze-im-internet.de, Hinweise Nr. 6 | XML „insbes. für Nutzer, die … über automatisierte Verfahren weiterverarbeiten möchten“, `gii-toc.xml` tagesaktuell | offizielle Quelle für den Korpus |
| § 2 Abs. 1 RDG | Rechtsdienstleistung ist eine Tätigkeit in konkreten **fremden** Angelegenheiten | eigene Fälle sind der Normalfall |
| § 6 RDG | Unentgeltlich ist erlaubt. Die Anleitungspflicht (Abs. 2) gilt nur **außerhalb** familiärer oder ähnlich enger Beziehungen | Familie ja. Ein öffentlicher Hub-Eintrag ist **nicht** Teil dieser Spec |

Die Oberfläche zeigt dauerhaft einen kurzen Hinweis: „Keine Rechtsberatung. Bei Fristen, Klagen und
Unsicherheit: Anwalt oder Beratungsstelle.“

## 4. Bausteine

### 4.1 Gesetzeskorpus (global, nicht pro Projekt)

- **Quelle:** `https://www.gesetze-im-internet.de/gii-toc.xml`, das sind 6.141 Einträge mit je `…/xml.zip`
  (Stand 20.10.). DTD `gii-norm.dtd 1.01`.
- **Ablage:** in der Kern-DB (SQLite `sessions.db`, wie alle Module, Präfix `module_legal_`). Tabellen `legal_laws` (Kürzel, Titel, Stand-Kommentar, Abrufdatum, Hash) und `legal_norms`
  (Gesetz, Bezeichnung `§ 536c`, Überschrift, Text, Absätze, Reihenfolge). Gemessen beim BGB: 467 KB ZIP,
  2.841 `<norm>`, 2,49 Mio. Zeichen XML, Stand „zuletzt geändert durch Art. 6 G v. 23.7.2026“.
- **Umfang:** Start mit einer festen **Kernliste** des Alltagsrechts. Alle Kürzel sind gegen `gii-toc.xml` vom
  20.10. geprüft und dort vorhanden:
  - **Zivil- und Verfahrensrecht:** `bgb, bgbeg, zpo, gvg, rvg, gkg_2004, uwg_2004, vvg_2008, pflvg`
  - **Wohnen und Immobilien:** `betrkv, heizkostenv, woflv, woeigg, gbo, bbaug, erbbauv, grestg_1983, beurkg`
  - **Familie:** `famfg, famgkg, versausglg, gewschg, lpartg, bkgg_1996, beeg, uhvorschg, erbstg_1974`
  - **Sozialrecht:** `sgb_1, sgb_2, sgb_5, sgb_8, sgb_10, sgb_11, sgb_12`
  - **Verwaltung:** `vwvfg, vwgo`
  - **Strafrecht und Bußgeld:** `stgb, stpo, owig_1968, jgg, btmg_1981, stvo_2013, stvg`
  - **Arbeit, Steuer, Daten:** `burlg, kschg, arbzg, estg, bdsg_2018, tkg_2021, ttdsg, ddg`
  - **Grundlagen:** `gg, rdg, urhg`
  - Zusammen 54 Gesetze.
  - Till sagte am 20.10. „das sollte alles sein“. Beim Prüfen stellte sich heraus, dass die erste Liste mit 33
    Gesetzen das **Verfahren in Familiensachen** (FamFG), das **Wohnungseigentum** (WEG) und das **Baugesetzbuch**
    nicht enthielt. Das materielle Familienrecht steht im BGB (4. Buch).
  Weitere Gesetze lassen sich in der Oberfläche nachladen, jedes aus der toc-Liste.
- **EU-Recht steht nicht in gesetze-im-internet.** Die **DSGVO** fehlt dort (geprüft 20.10.). Sie kommt aus
  EUR-Lex (CELEX 32016R0679) als eigene Quelle, Umfang: die Artikel als Normen. Die Weiterverwendung von
  EUR-Lex-Inhalten ist **vor L1 zu prüfen**. Bis dahin gilt: Art.-Zitate der DSGVO sind „nicht im Korpus“ und nicht „falsch“.
- **Aktualisierung:** ein Modul-Job einmal täglich nachts. Er vergleicht Stand und Hash und lädt nur Geänderte.
  Alte Fassungen bleiben mit Gültig-bis-Datum erhalten, damit ein Brief vom März seinen Stand behält.
- **Suche:** SQLite **FTS5** (`unicode61 remove_diacritics 2`, im Kern-venv vorhanden, SQLite 3.46.1, geprüft 20.10.)
  über Überschrift und Text, dazu ein exakter Treffer auf Bezeichnung und Kürzel (`536c BGB`, `§ 536 c`,
  `BGB 536c`).
  - Ob die Suche gut genug ist, misst L0 an 20 echten Fragen. Deutsche Wortformen (Mangel/Mängel, Mieter/Mietern)
    sind die Schwachstelle von FTS ohne Stemmer.
  - **Bedeutungssuche (Embeddings) erst später**, optional: Auf .2 antwortet derzeit kein Ollama
    (Port 11434, gemessen 20.10.), und Cloud-Embeddings kosten.
  - Die Suche ist so gebaut, dass `aembed_batch` später dazukommen kann.
- **Landesrecht** (z. B. Bauordnung, Nachbarrecht NRW): nicht in dieser Spec, eigene Quelle je Land.

### 4.2 Fall = Projekt

- **Fall anlegen** in „Recht“ → „Neuer Fall“:
  - legt ein **Projekt** an (Name `Recht – <Kurztitel>`) samt Fall-Datensatz und Rechts-Agent (§ 4.6)
  - **Rechte (Till 20.10.: „jeder nach seinen Rechten“):**
    - Capability `module.legal` erlaubt Modul nutzen, eigene Fälle sehen, Gesetze suchen
    - Capability `legal.create_case` erlaubt Fälle anlegen
    - beide Standard `admin_only`, der Admin vergibt sie pro Person bzw. Gruppe in der Freigabe-Verwaltung
  - Wer einen Fall anlegt, wird Projekt-Admin und lädt weitere Mitglieder mit Rolle `read` oder `write` ein
    (Kern-Projektverwaltung)
  - Im Fall selbst zählt danach nur die Projektrolle
- **Tabelle `legal_cases`** (`project_id` UNIQUE): Titel, Rechtsgebiet, Status (offen, wartet, erledigt),
  Sachverhalt, Ziel, Gegenseite, eigener Anwalt, Aktenzeichen (fremd und eigen), **Bundesland** für Feiertage
  (Till 20.10.: pro Fall wählbar; Vorschlag beim Anlegen ist das Bundesland des letzten Falls des Nutzers).
- **`legal_parties`**: Name, Rolle (Gegenseite, Anwalt, Behörde, Zeuge, ich), Anschrift, Kontakt.
- **`legal_deadlines`**: Bezeichnung, Ereignisdatum, Fristart, Ergebnisdatum, Rechenweg (§ 4.4), Status.
- **`legal_correspondence`**: eingehend oder ausgehend, Datum, Absender und Empfänger, Betreff, Text, Zustellweg,
  Nachweis (z. B. Einschreiben-Nummer).
- **`legal_notes`**: Recherche-Notizen des Agenten mit Normbelegen (§ 4.5).
- **Rechte:** Wie der Storyteller (`project_access`) gelten System-Admin oder die Projektrolle: `read` sieht alles,
  `write` ändert und übernimmt Vorschläge.
- **Alles liegt in der DB**, nicht im Projektordner. Begründung: Projekt-Agenten haben `file_read` und
  `shell_exec` (`agents/_defaults.py`). Dateien im Workspace wären an der Vault-PIN vorbei lesbar.
- **Löschen:** Wird das Projekt gelöscht, verwaist der Fall. Ein Modul-Job räumt Fälle ohne Projekt nach
  30 Tagen ab, eine Sicherung erfolgt vorher als JSON ins Archiv. Einen Kern-Hook für Projekt-Löschungen gibt es heute
  nicht (geprüft `archive/deletion.py`).

### 4.3 Menüpunkt „Recht“ (Oberfläche, `"vault": true`)

- **Fälle:** Liste mit Status, nächster Frist (Ampel) und letztem Schreiben. „Neuer Fall“ führt durch ein Aufnahme-
  Formular: Was ist passiert, seit wann, wer ist beteiligt, was willst du erreichen, welche Fristen sind bekannt.
- **Fallakte:** Reiter Übersicht · Beteiligte · Fristen · Schriftverkehr · Recherche · Vorschläge.
  Ein Knopf „Mit dem Rechts-Agenten sprechen“ öffnet den Projekt-Chat.
- **Gesetze:** Suche, Norm-Ansicht mit Stand und Link zur amtlichen Seite, „Zur Fallakte“.
- **Briefe:** Vorschlag ansehen, bearbeiten, übernehmen und als PDF herunterladen.
- Die Seite selbst lädt nichts ohne Klick, so wie im Vault.

### 4.4 Fristenrechner (ohne KI)

- §§ 187, 188, 193 BGB fest programmiert:
  - Ereignistag zählt nicht mit (§ 187 Abs. 1)
  - Tage, Wochen und Monate nach § 188, Monatsende-Regel nach § 188 Abs. 3
  - fällt das Ende auf Samstag, Sonntag oder einen Feiertag, verschiebt es sich auf den nächsten Werktag (§ 193)
- Feiertage bundesweit plus **Bundesland des Falls** (pro Fall wählbar, § 4.2), eigene Tabelle. Bewegliche Feiertage über die
  Osterformel (geprüft: 05.04.2026, 28.03.2027). Keine neue Abhängigkeit.
- Die Ausgabe nennt immer den **Rechenweg** mit Normen, z. B. „Zugang Mo 20.10. → Beginn 21.10. →
  2 Wochen → Ende Mo 03.11.“.
- Werkzeug `legal_deadline` und Formular in der Fallakte.

### 4.5 Belegpflicht und Zitat-Prüfer (ohne KI)

- Jede Norm, die in einer Antwort, Notiz oder einem Brief vorkommt, erkennt eine Regel:
  - `§ 536c BGB`, `§§ 535 ff. BGB`, `Art. 15 DSGVO`, `§ 536 Abs. 1 S. 2 BGB` usw.
  - die Normen werden im Korpus aufgelöst, das Ergebnis ist **belegt** (mit Stand) oder **unbekannt**
- **Wörtliche Zitate** in Anführungszeichen hinter einer Norm werden gegen deren Text geprüft. Abweichungen
  werden angezeigt.
- Werkzeug `legal_check_citations` für den Agenten. In der Oberfläche markiert jeder Vorschlag unbekannte Normen rot.
  **Unbekannte Normen blockieren das Übernehmen nicht**, der Nutzer sieht die Markierung aber deutlich.
- Entscheidungen (Az., Gericht, Datum) prüft L4 gegen OpenLegalData.

### 4.6 Agent-Werkzeuge und Rechts-Agent

- Alle Werkzeuge arbeiten **nur im Projekt der Sitzung** (`ToolContext.project_id`). Die Rechte hängen an der
  Projektrolle, so wie der Storyteller `scope()` nutzt.
- Lesen: `legal_case` (Fallakte), `legal_search` (Gesetze), `legal_norm` (Wortlaut + Stand),
  `legal_deadline` (Rechner), `legal_check_citations`.
- Vorschläge: `legal_propose_letter`, `legal_propose_deadline`, `legal_propose_party`, `legal_note`.
  Der Agent **ändert nie direkt**. Der Mensch übernimmt in der Oberfläche.
- **`sensitive_tools`:** alle Fall-Werkzeuge mit Stufe `privat`. Die reinen Gesetzes-Werkzeuge
  (`legal_search`, `legal_norm`, `legal_deadline`) bleiben `normal`.
- **Rechts-Agent je Fall** (beim Anlegen):
  - Werkzeuge: die `legal_*`-Werkzeuge, dazu `web_search`, `fetch_url`, `load_skill` und `list_skills`
  - **Keine** Werkzeuge mit Außenwirkung und keine Datei- oder Shell-Werkzeuge
  - Systemprompt: belegen statt behaupten, Unsicherheit benennen, Fristen immer mit Rechenweg, an Anwalt oder
    Beratungsstelle verweisen, wenn Klage, Strafrecht oder hohe Summen im Spiel sind.
- **Skill `rechtsbrief`** im Modul: Aufbau, Ton und Pflichtangaben je Brieftyp.

### 4.7 Brief-Werkstatt

- **Vorlagen:**
  - Mangelanzeige mit Fristsetzung (§§ 536, 536c BGB)
  - Widerspruch gegen Bescheid
  - Fristsetzung oder Mahnung
  - Kündigung
  - DSGVO-Auskunft (Art. 15 DSGVO, erst mit EUR-Lex-Quelle belegbar)
  - Bitte um Akteneinsicht
  - Anschreiben an den eigenen Anwalt mit Sachverhalt
- **Prüfliste vor dem Übernehmen:**
  - Absender, Empfänger und Datum vorhanden
  - Aktenzeichen, falls bekannt
  - Frist als **Datum**, nicht „binnen 14 Tagen“ ohne Datum
  - Normen belegt (§ 4.5)
  - Zustellweg vermerkt (Einwurf-Einschreiben, Bote, Fax mit Sendebericht)
  - Anlagenliste
- **Gegenlesen:** ein zweiter Durchgang mit eigenem Prompt prüft Ton, Widersprüche zum Sachverhalt und
  Lücken. Das Ergebnis steht als Hinweisliste daneben, der Brief bleibt unverändert.
- **PDF:** DIN 5008 Form B (Anschriftfeld, Bezugszeichen, Betreff, Seitenzahl).
  - **Druckansicht im Browser** (CSS `@page`, „Als PDF speichern“), keine neue Abhängigkeit. Im Kern-venv gibt es
    keine PDF-Bibliothek (geprüft: reportlab, weasyprint, fpdf, pypdf fehlen). Till hat am 20.10. bestätigt, dass das
    reicht.
- Ein übernommener Brief wandert in den Schriftverkehr (ausgehend, Status „Entwurf“, bis der Nutzer
  „versendet am … per …“ einträgt). **Kein automatischer Versand.**

### 4.8 Rechtsprechung (L4)

- OpenLegalData-API (`de.openlegaldata.io/api/cases/search/`), Lesen öffentlich, 425.139 Entscheidungen (20.10.).
- Abruf **nur bei Bedarf** durch das Werkzeug `legal_cases_search`, kein Komplettdownload. Treffer speichert der Agent
  nur als Verweis plus Leitsatz in der Notiz.
- **Lizenz der Datenbank** vor L4 prüfen. Gerichtsentscheidungen selbst sind nach § 5 UrhG frei.

## 5. Schutz

- `"vault": true`: Oberfläche und API brauchen die PIN.
- Fall-Werkzeuge mit Stufe `privat`: Datamining anderer Agenten sieht diese Sitzungen nur mit passender Freigabe.
- Rechts-Agent ohne Außenwirkung (§ 4.6). Damit hat er nach `knowledge-spaces.md` §2.2 höchstens `normal` Außenwirkung,
  also keine.
- Keine Fall-Daten im Log, nur IDs.
- Ein Agent kommt nur über das eigene Projekt an Fälle, nie über eine freie `project_id`.

## 6. Etappen

| Etappe | Inhalt | Abnahme |
|---|---|---|
| **L0** | Probe: Kernliste laden, Zeit, Größe und Suchqualität messen (20 echte Fragen) | Messwerte in der Spec |
| **L1** | Korpus + Aktualisierung + Suche + `legal_search`/`legal_norm` + Gesetzes-Ansicht | § 536c BGB per Suche gefunden, Wortlaut = amtliche Seite, Stand stimmt |
| **L2** | Fall = Projekt, Fallakte, Beteiligte, Fristenrechner, Rechts-Agent, Rechte | Fall anlegen → Projekt + Agent. Mitglied mit Rolle `read` sieht und ändert nichts. Fristen gegen 15 Handfälle |
| **L3** | Vorschläge + Brief-Werkstatt + Prüfliste + Druckansicht | Pilot: Mangelanzeige Mietsache (Task 5d49bee3) |
| **L4** | Zitat-Prüfer vollständig + Gegenlesen + Rechtsprechung | 30 Zitate, davon 10 absichtlich falsch → alle 10 rot |
| **L5** | Dokumente hochladen (PDF/Bild), Text erkennen, durchsuchen | eigene Spec |

## 6a. L0 – Messung (20.10.2026, Wegwerf-Probe außerhalb der Produktiv-DB)

| Messung | Wert |
|---|---|
| Download der 54 Gesetze (`xml.zip`, 0,5 s Pause je Abruf) | **33 s**, zusammen **5,0 MB** ZIP. Größte: StVO 742 KB, SGB V 624 KB, BGB 467 KB |
| Normen nach dem Filtern (ohne Inhaltsübersicht, weggefallene Normen, leere Texte) | **10.715**, z. B. BGB 2.486, ZPO 1.053, StGB 519 |
| Aufbau SQLite + FTS5 | **3 s**, DB **26 MB** |
| Suche | **2–3 ms** pro Anfrage |
| Treffer bei Laienfragen direkt („Wohnung zu heiß, Mangel melden“) | Top 1: 4/20 · Top 5: 9/20 · **Top 10: 13/20** |
| Treffer, wenn der Agent in Fachbegriffe übersetzt („Mangel Mietsache Anzeige Mieter“) | **Top 1: 15/20 · Top 5: 19/20** · Top 10: 19/20 |

**Befunde:**
- **Kürzel:** `<jurabk>` lautet z. B. „OWiG 1968“ bzw. „BDSG 2018“. Das richtige Zitierkürzel steht in **`<amtabk>`**
  (OWiG, BDSG). Der Parser nimmt `amtabk`, sonst `jurabk`. Das hat 2 von 20 Testfällen repariert.
- **815 Normen ohne Überschrift** (vor allem VwGO, GVG, GG, GBO). Für diese Normen sucht der Index
  schon über **die Überschrift der Gliederungseinheit** (z. B. VwGO § 70 → „8. Abschnitt Besondere Vorschriften
  für Anfechtungs- und Verpflichtungsklagen“) und über den Text.
  - Mit „Widerspruchsfrist Verwaltungsakt“ fand die Suche VwGO § 70 nicht unter den ersten 10. Mit
    „Widerspruch Frist Verwaltungsakt“ (getrennte Wörter) stand er auf **Platz 2**. Zusammengesetzte Wörter sind
    die Schwachstelle der Wortsuche.
  - → Skill-Regel: Wortverbindungen getrennt suchen. Bei Normen ohne Überschrift zeigt die Ergebnisliste die
    Gliederung an.
- Die BetrKV hat tatsächlich nur 2 Paragrafen, der Katalog steht in § 2.

**Entscheidung für L1** (folgt aus der Messung):
- Die Volltextsuche reicht, **wenn der Agent die Frage vorher in Gesetzessprache umformuliert**. Die
  Werkzeug-Beschreibung von `legal_search` und der Skill sagen das ausdrücklich („Suche mit Fachbegriffen; bei wenig
  Treffern zweite Formulierung“). Ohne Umformulierung fehlen 7 von 20.
- **Embeddings nicht in L1.** Das eingestellte Kern-Embedding ist `text-embedding-3-small` (OpenAI, kostenpflichtig;
  Messung auf .2 am 20.10.). Der Korpus hat ca. **3,8 Mio. Token** (13,2 Mio. Zeichen, Faustregel 3,5 Zeichen/Token).
  Den aktuellen Preis konnte ich auf der OpenAI-Preisseite nicht finden, er ist also nicht bestätigt. Laut Spec gilt
  „nur kostenlos“. Bedeutungssuche kommt erst mit einem lokalen Modell (Ollama auf .2 ist heute aus).

## 7. Nicht in dieser Spec

- Öffentlicher Hub-Eintrag bzw. Weitergabe an Fremde (RDG § 6 Abs. 2)
- Landesrecht, EU-Recht außer der DSGVO (§ 4.1), Verwaltungsvorschriften
- Automatischer Versand (Mail, Fax, beA)
- Bezahl-Datenbanken (juris, beck-online)

## 8. Entscheidungen zu den offenen Punkten (Till, 20.10.2026)

1. **Kernliste:** „das sollte alles sein“. Sie umfasst Zivil-, Immobilien-, Straf- und Familienrecht, ergänzt um FamFG, WEG und
   BauGB (§ 4.1, 54 Gesetze).
2. **Fälle anlegen:** „jeder nach seinen Rechten“, über die Capabilities `module.legal` und `legal.create_case` (§ 4.2).
3. **PDF:** Die Druckansicht im Browser reicht (§ 4.7).
4. **Feiertage:** Das Bundesland ist pro Fall wählbar (§ 4.2, § 4.4).

Noch offen, nicht blockierend für L0/L1: Die EUR-Lex-Weiterverwendung für die DSGVO wird vor dem Einbau geprüft.
