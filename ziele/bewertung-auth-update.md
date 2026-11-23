# Zieldokument: Auth-Wächter für alle API-Routen + Update mit Sicherung und Rückweg

> **Status:** FREIGEGEBEN (Till, 23.11.2026: „ok mache das“)
> **Auslöser:** Externe Bewertung vom 23.11.2026, Sammel-Task `f9b63a15`.
> **Tasks:** `589ff768` (Auth-Wächter), `5b8ad460` (Update mit Rückweg)
> **Repo:** Kern `hydrahive2`

## 1. Auth-Wächter (Task 589ff768)
Befund vom 23.11.2026 (Kern 7aacae35): Die App hat 542 API-Routen. 14 davon haben keine Auth-Abhängigkeit, und das ist bei allen 14 Absicht, weil sie selbst prüfen:
- `/api/auth/login`, `/api/health`
- `/api/files` mit Token im Link (`get_current_user_optional` + `resolve_credential`)
- `/api/agentlink/dashboard-auth` (Cookie-Prüfung für nginx)
- Butler-Webhook, WhatsApp-Eingang, Compute-Enroll
- 7× `/api/peering/*` (Ed25519-Signatur)

Bisher hindert nichts daran, dass eine neue Route ohne Auth dazukommt.

Regeln:
1. Ein Test im Kern-CI läuft über `app.routes` (die echte App mit geladenen Modulen, soweit das in der CI möglich ist). Für jede API-Route prüft er rekursiv die Abhängigkeitskette auf eine Auth-Abhängigkeit (require_auth, require_principal, require_admin o. ä.; die echte Liste steht im Code).
2. Ausnahmen stehen in einer Liste mit Methode, Pfad und Begründung. Gibt es eine Route ohne Auth, die nicht auf der Liste steht, wird der Test rot und die Meldung nennt Pfad und Methode.
3. Auf der Liste steht nur, was wirklich offen sein muss. Ein Eintrag ohne Begründung ist ein Fehler. Ein Listeneintrag, zu dem es keine Route mehr gibt, ist ebenfalls ein Fehler (damit die Liste nicht veraltet).
4. Jede Ausnahme bekommt einen Test, der zeigt, dass sie ohne gültige Anmeldung bzw. Signatur nichts preisgibt (401/403/404 oder leere/feste Antwort). Login und Health sind davon ausgenommen.
5. Module-Routen: Wenn die Kern-CI die Module nicht lädt, soll der Wächter als wiederverwendbare Funktion bereitstehen, damit `hydrahive2-modules` ihn später nutzen kann. Ein Folge-Task reicht dafür, Umsetzung im Modul-Repo ist nicht Teil dieses Auftrags.

## 2. Update mit Sicherung und Rückweg (Task 5b8ad460)
Befund: `installer/update.sh` (919 Zeilen) und `installer/update-mac.sh` legen keine Sicherung an und haben keinen Rückweg. Scheitert der Bau, eine Migration oder der Start, bleibt der Server auf einem halben Stand stehen.

Vorgehen in zwei Schritten:
1. **Spec zuerst:** `docs/specs/update-rollback.md`, dazu ein Bestandsbild. Was ändert ein Update heute alles (git, venv, npm-Build, Modul-Kopien, systemd-Units, nginx, Migrationen in den DBs beim Start)? Was lässt sich zurückdrehen und was nicht (z. B. apt-Pakete, Container)? Welche DBs, wie groß sind sie, und wie viel kostet eine Sicherung an Zeit und Platz? Rollback-Ablauf, Fehlerfälle, Mac-Unterschiede, Aufbewahrung (z. B. die letzten 2 Sicherungen). **Till gibt die Spec frei, bevor gebaut wird.**
2. **Danach umsetzen** in kleinen Etappen laut Spec.

Rahmen für die Spec:
- Vor dem Update: alten Commit merken und die Kern-DBs konsistent sichern (`sqlite3 .backup` oder Python `backup()`, nicht `cp` bei laufendem Dienst). Die Konfiguration unter `/etc/hydrahive2` ebenfalls sichern. Ist nicht genug Platz frei, bricht das Update vor jeder Änderung mit einer klaren Meldung ab.
- Nach dem Update: Dienst aktiv, `/api/health` ok, Migrationen durchgelaufen. Erst danach gilt das Update als erfolgreich.
- Bei Fehlschlag automatisch zurück: alter Commit, alter Build, DB-Sicherung wieder einspielen, Dienst starten. Das Update-Fenster zeigt `HH-UPDATE-ENDE: fehler <Grund> – auf <alter Commit> zurückgesetzt`.
- Der Rückweg selbst darf nie zu Datenverlust führen: Bevor die Sicherung eingespielt wird, kommt der kaputte Stand zur Seite und wird nicht gelöscht.
- Modul-Updates: Die alte Modulversion bleibt erhalten, bis die neue läuft.

## 2b. Butler-Webhook ohne Secret (Task 44fffa23)
> Freigegeben von Till am 23.11.2026, Variante **b** (Secret automatisch erzeugen).

Befund: `api/routes/butler.py:116` prüft `X-Webhook-Secret` nur, wenn das Projekt ein `webhook_secret` hat. Neue Projekte bekommen bereits eines (`projects/config.py:58`), Altprojekte ohne Secret nehmen aber jeden POST an.

Regeln:
1. Eine einmalige, idempotente Migration beim Start erzeugt für jedes Projekt ohne `webhook_secret` eines (`secrets.token_urlsafe(32)`) und schreibt einen Audit-Eintrag (`webhook_secret_generated`).
2. Fehlt dem Projekt trotzdem ein Secret (Race, kaputte Konfig), lehnt die Route ab (401 `webhook_secret_required`). Ungeprüft durch geht nichts mehr. Der Kommentar zum alten „insecure Modus“ wird entfernt.
3. Im Butler/Projekt-Cockpit gibt es einen Hinweis für betroffene Projekte: Ein Secret wurde automatisch erzeugt, externe Absender müssen den Header `X-Webhook-Secret` setzen. Das Secret lässt sich dort anzeigen und kopieren, der vorhandene Knopf zum Neu-Erzeugen bleibt.
4. Das xfail im Test `test_butler_webhook_projekt_ohne_secret` wird entfernt, der Test ist jetzt grün und prüft die Ablehnung.

## 3. Nicht-Ziele
- Keine Prozess-Isolation von Modulen (Idee `dea1413d`).
- Kein Commit-Pinning bzw. keine Signatur für Updates (Task `2c73f4b5`).
- Keine Umstellung der Legacy-Routen auf principal (Task `19699ab0`).

## 4. Abnahme-Punkte
| # | Prüfung |
|---|---|
| W1 | Auth-Wächter-Test im Kern: geht über alle API-Routen der echten App, Ausnahmeliste mit Begründung je Eintrag. Gegenprobe: eine Test-Route ohne Auth wird hinzugefügt → Test rot mit Pfad und Methode in der Meldung (im PR belegt) |
| W2 | Veraltete Listeneinträge (Route existiert nicht mehr) oder Einträge ohne Begründung → Test rot |
| W3 | Für jede Ausnahme außer Login/Health ein Test: ohne gültige Anmeldung/Signatur keine Daten |
| W4 | PR mit grüner CI, Review durch hydrahive-reviewer und hydrahive-security-reviewer, per Merge-Commit auf main |
| U1 | Spec `docs/specs/update-rollback.md` mit Bestandsbild (was ändert ein Update, was ist umkehrbar, DB-Größen/Zeit), Ablauf, Fehlerfällen, Mac-Unterschieden; als PR eingereicht und Till zur Freigabe vorgelegt |
| B1 | Migration: Projekt ohne Secret bekommt beim Start eines, zweiter Lauf ändert nichts, Audit-Eintrag vorhanden (Test) |
| B2 | Webhook auf Projekt ohne Secret → 401, mit falschem → 403, mit richtigem → 202 (Test); das xfail ist entfernt |
| B3 | Hinweis im Cockpit für Projekte mit automatisch erzeugtem Secret, Secret kopierbar (Frontend, i18n de/en) |
| B4 | PR mit grüner CI, Review durch hydrahive-reviewer und hydrahive-security-reviewer, per Merge-Commit auf main |
| R1 | Spec-PR #753 (update-rollback, von Till am 23.11.2026 freigegeben: „alle Vorschläge ok“) mit main aktualisiert, von hydrahive-reviewer gesichtet, CI grün, per Merge-Commit auf main |
| U2 | Etappe U2 laut `docs/specs/update-rollback.md` §7: Frontend-Bau in `dist.neu` + atomarer Tausch (Linux `update.sh`, Mac `update-mac.sh`, `_frontend_build` der Module). Test: Bau scheitert → `dist` unverändert, laufendes Frontend heil. PR mit grüner CI, Review hydrahive-reviewer, Merge-Commit auf main |
| U3 | Etappe U3 laut `docs/specs/update-rollback.md` §3.1/§6/§7: Phase A in `update.sh` (Sperre per flock, `OLD_COMMIT`/`meta.env` vor `hh_git_update`, Re-exec ohne zweite Sicherung, Platzprüfung, `db_snapshot.py` mit `VACUUM INTO` + `quick_check` + zstd, Sicherung von Config/Units/nginx/sudoers/`dist`/`frontend/src/modules`, venv nur bei Änderung, Aufbewahrung der letzten 2, Anleitung für einen Rückweg von Hand im Log); **noch kein automatischer Rückweg**. Tests: wenig Platz → Abbruch vor `git pull` mit „nichts verändert“; Sicherung lesbar und `quick_check ok`; Sperre verhindert einen zweiten Lauf; Re-exec legt keine zweite Sicherung an. PR mit grüner CI, Review durch hydrahive-reviewer und hydrahive-security-reviewer (root, /etc-Sicherung), Merge-Commit auf main |
