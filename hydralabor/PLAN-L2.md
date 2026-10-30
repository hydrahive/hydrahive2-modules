# Hydra-Labor – Bauplan Etappe L2 (GitHub: verbinden, einreichen, Fehler melden)

> Grundlage: `SPEC.md` (freigegeben 30.10.), L1 gemergt (#323). Ziel von L2: Der Admin verbindet sein GitHub-Konto
> ohne Passwort/Token-Eintippen, und aus dem Labor wird per Knopf ein **PR von seinem Fork** bzw. ein **Issue** bei
> `hydrahive/hydrahive2.0` (Kern) oder `hydrahive/hydrahive2-modules` (Module). Till prüft und übernimmt.
> Der Container sieht den GitHub-Zugang **nie**.

## Befunde vorab (30.10.)

- **Device-Flow** geht ohne Client-Secret: `POST github.com/login/device/code` liefert Code + `github.com/login/device`
  (gemessen mit der öffentlichen Client-ID der GitHub-CLI: `user_code`, `expires_in` 899 s, `interval` 5 s).
  Danach `POST github.com/login/oauth/access_token` mit `grant_type=urn:ietf:params:oauth:grant-type:device_code`
  im Abstand `interval`, bis `access_token` kommt (oder `expired_token` / `access_denied`).
- **Bündel statt Token im Container** funktioniert: `git bundle create <datei> <basis>..HEAD` im Container,
  auf dem Server `git fetch <bündel> HEAD:labor/…` in ein Arbeits-Repo, dann `git push` mit Token (gemessen lokal).
- `hydrahive` ist auf GitHub ein **Nutzerkonto**, keine Organisation → OAuth-App unter
  Settings → Developer settings → OAuth Apps des Kontos `hydrahive`.
- Kern hat `credentials/_crypto.encrypt/decrypt` (AES-GCM, Master-Schlüssel des Servers) und
  `credentials/redaction.SECRET_PATTERNS` (Geheimnis-Muster) → beides wird genutzt, nicht nachgebaut.

## Bausteine

1. **GitHub-Verbindung** (`backend/github_auth.py`)
   - `start()` → Device-Code anfordern (Scope **nur `public_repo`**), `user_code` + Link zurückgeben,
     `device_code` nur im Speicher des Servers.
   - Hintergrund-Abfrage im Abstand `interval` (bei `slow_down` +5 s), Abbruch nach `expires_in`.
   - Token **verschlüsselt** in `module_hydralabor_github` (eine Zeile): `token_enc`, `login`, `scopes`, `connected_at`.
     Nie in Logs, nie in Antworten, nie im Container. Nach dem Verbinden: `GET /user` → `login`; Scopes aus dem
     Antwortkopf `X-OAuth-Scopes` prüfen (mehr als `public_repo` → ablehnen und nicht speichern).
   - „Trennen“: Token bei GitHub widerrufen geht ohne Secret nicht → lokal löschen und Link auf
     `github.com/settings/applications` zeigen („dort kannst du den Zugang auch bei GitHub entfernen“).
   - Client-ID steht im Modul (`backend/github_app.py`), Umgebungsvariable `HH_LABOR_GITHUB_CLIENT_ID` überschreibt
     (für das Test-Konto auf hydratest).
2. **Forks** (`backend/github_repos.py`): Für Kern und Module prüfen, ob `<login>/<repo>` ein Fork von
   `hydrahive/<repo>` ist; sonst `POST /repos/hydrahive/<repo>/forks` und warten, bis er da ist (bis 60 s).
   Ein gleichnamiges Repo, das **kein** Fork ist → klare Meldung, nichts überschreiben.
3. **Klon im Labor auf den Fork umstellen**: `origin` bleibt das öffentliche Haupt-Repo (zum Aktualisieren),
   zusätzlich nichts mit Zugangsdaten. Das Modul braucht im Container keinen Fork-Remote – es schiebt selbst.
4. **Änderung einreichen** (`backend/submit.py`, Auftrag `submit` im Hintergrund wie in L1)
   - Eingaben: Ziel (`core` / `modules`, Vorschlag aus den geänderten Dateien), Titel (≤ 120 Zeichen),
     Beschreibung (≤ 4000 Zeichen).
   - **Vorprüfung im Container** (alles grün, sonst Abbruch mit Liste der Gründe):
     a) Es gibt Änderungen gegenüber `origin/main` (Commits oder ungesicherte Änderungen → das Modul legt
        einen Commit an, Autor = GitHub-`login` + `<id>+<login>@users.noreply.github.com`).
     b) **Geschützte Pfade** nicht berührt: `.github/`, `installer/`, `scripts/check_*`, `LICENSE*`,
        `SECURITY.md`, `docs/specs/` (Kern) bzw. `.github/`, `scripts/`, `hub.json`, `LICENSE*` (Module).
        Liste im Modul mit Begründung.
     c) **Kein Geheimnis im Diff** (Kern-Muster `SECRET_PATTERNS` + `gho_`/`ghu_`/`ghs_`/`ghr_`).
     d) **Größe**: ≤ 50 Dateien und ≤ 3 000 geänderte Zeilen.
     e) **Tests**: Kern → `pytest -q -n 2 core/tests`; Module → `pytest` in jedem geänderten Modul,
        dazu `scripts/check_version_bump.py origin/main` und `scripts/check_test_safety.py`.
   - **Bündel**: `git bundle create /tmp/labor.bundle origin/main..HEAD` im Container, mit `incus file pull` holen
     (Größe ≤ 50 MB), Container-Datei löschen.
   - **Schieben** (auf dem Server, in einem frischen Arbeits-Repo unter dem Datenordner des Moduls):
     `git fetch` des Bündels → Branch `labor/<kurzname>-<JJJJMMTT-HHMM>` → `git push` an den Fork. Der Token geht
     nur per `http.extraHeader` aus einer Umgebungsvariable an git, **nie** in eine URL oder Datei.
     Arbeits-Repo wird danach gelöscht.
   - **PR** `POST /repos/hydrahive/<repo>/pulls` (head `<login>:<branch>`, base `main`), Text: Beschreibung,
     Prüfergebnis (Zahlen), Hinweis „eingereicht über Hydra-Labor“, HydraHive-/Modul-Version. Label `labor` nur,
     wenn GitHub es erlaubt (Fremde dürfen keine Labels setzen → Fehler wird ignoriert, Till setzt es).
   - Gespeichert in `module_hydralabor_submissions`: Ziel, Titel, Branch, PR-Nummer/-Link, Stand, Zeit.
5. **Stand der Einreichungen**: Knopf „Aktualisieren“ (kein Dauer-Abfragen) holt je offenem PR
   `state`/`merged`/letzten Kommentar von Till → „eingereicht“, „übernommen“, „abgelehnt“ (+ Kommentar).
6. **Fehler melden** (`backend/report.py`): Formular „Was ist passiert / Was hast du erwartet / Schritte“, Ziel
   Kern oder Module. Das Modul hängt an: HydraHive-Version, Modul-Versionen, Betriebssystem. **Keine Logs** in L2
   (Logs nach Rückfrage + Filter kommen später). Text vor dem Senden durch `redact_detected` des Kerns.
   `POST /repos/hydrahive/<repo>/issues`.
7. **GitHub-Zugriffe** (`backend/github_api.py`): nur `api.github.com` und `github.com/login/...` (feste URLs),
   Zeitlimits, Ratenbegrenzung beachten (`X-RateLimit-Remaining` 0 → Meldung), Fehlercodes statt Rohtexten.

## Oberfläche

- **Assistent**: neuer Schritt „Mit GitHub verbinden“ vor „Labor anlegen“. Optional – ohne GitHub geht das Labor
  wie in L1, nur ohne Einreichen. Zeigt den Code groß, Knopf „Code kopieren“, Link „GitHub öffnen“, wartet sichtbar.
  Ohne Konto: Link „Konto anlegen“.
- **Labor-Seite**: Kasten „GitHub“ (verbunden als `<login>` / Trennen / Verbinden). Knöpfe **„Änderung einreichen“**
  und **„Fehler melden“** (eigene Dialoge), Liste „Meine Einreichungen“ mit Stand und Link.
- Fortschritt beim Einreichen: Vorprüfung (je Punkt grün/rot), Tests, Schieben, PR angelegt → Link.

## Sicherheit

- Token: verschlüsselt, nie in Antworten/Logs/Container/Dateien; Scope genau `public_repo`.
- Der Labor-Agent hat keinen Weg zum Einreichen (kein Werkzeug) – nur der Admin über die Oberfläche.
- Bündel aus dem Container ist **nicht vertrauenswürdig**: nur `git fetch` daraus (keine Hooks, kein Checkout von
  Dateien auf dem Server: Arbeits-Repo ist `--bare`), Größengrenze, Datei danach weg.
- Branch-Name und PR-Text werden vom Modul gebaut bzw. begrenzt; der Commit-Inhalt kommt aus dem Labor und wird
  von Till auf GitHub geprüft.
- Push nur an `<login>/<repo>`, nie an `hydrahive/*`.

## Tests

- Rot zuerst. GitHub als Attrappe (feste Antworten, Aufrufe mitschreiben), incus wie in L1.
- Device-Flow: Code, Warten, `slow_down`, `expired_token`, `access_denied`, falsche Scopes → nicht gespeichert.
- Token taucht in keiner Antwort, keinem Log, keinem incus-Aufruf auf (Test mit Erkennungs-Token).
- Fork: vorhanden / neu / gleichnamiges Nicht-Fork-Repo.
- Vorprüfung: je Punkt a–e ein roter Fall; geschützte Pfade; Geheimnis-Muster; Größe; Tests rot.
- Push: Token nur über Umgebung, Arbeits-Repo bare und danach weg, Ziel nur Fork.
- Mutanten, Gegenprobe, volle Reihe; **echt**: mit einem **Test-GitHub-Konto** und einem **Test-Repo** (nicht die
  echten `hydrahive`-Repos) auf hydratest – verbinden, Fork, einreichen, PR erscheint, Fehler melden, E2E 4 Breiten.

## Was Till einrichten muss

1. **OAuth-App** im Konto `hydrahive`: Settings → Developer settings → OAuth Apps → New OAuth App
   - Name „HydraHive Labor“, Homepage `https://github.com/hydrahive`, Callback-URL `https://github.com/hydrahive`
     (wird beim Device-Flow nicht benutzt, ist aber Pflichtfeld)
   - **„Enable Device Flow“ anhaken**
   - Mir die **Client-ID** geben (öffentlich, kein Secret nötig).
2. **Label `labor`** in `hydrahive2.0` und `hydrahive2-modules` – kann ich mit unserem Zugang anlegen, wenn du willst.
3. **Für die echte Probe**: ein zweites GitHub-Konto zum Testen (oder ich teste nur gegen ein Test-Repo unter
   `hydrahive`, siehe Frage 2).

## Offene Fragen an Till

1. Plugins (`hydrahive2-plugins`) schon in L2 als drittes Ziel – oder wie geplant in L3?
2. Echte Probe: Darf ich ein Test-Repo `hydrahive/labor-test` (öffentlich, danach löschen) anlegen und mit unserem
   Konto „von außen“ dorthin einreichen? Ein Fork des eigenen Repos geht bei GitHub nicht – für den Fork-Weg
   bräuchte ich ein **zweites Konto**. Ohne zweites Konto prüfe ich den Fork-Teil nur mit der Attrappe.

## Entscheidungen (Till, 30.10.)

- Bauplan freigegeben („so ist gut“). Till legt die OAuth-App an und gibt die Client-ID.
- Label `labor` in Kern- und Modul-Repo: lege ich an.
- **Annahmen** (Fragen nicht ausdrücklich beantwortet, Standard aus dem Plan):
  1. Plugins als drittes Ziel erst in L3.
  2. Echte Probe ohne zweites GitHub-Konto: Fork-Teil mit Attrappe, PR/Issue echt gegen ein Test-Repo
     `hydrahive/labor-test`, das danach gelöscht wird.
