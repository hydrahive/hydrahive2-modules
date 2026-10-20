-- Recht-Modul L1: Gesetzeskorpus aus gesetze-im-internet.de (legal/SPEC-LEGAL.md §4.1)
CREATE TABLE IF NOT EXISTS module_legal_laws (
  key TEXT PRIMARY KEY,                       -- Pfad bei gesetze-im-internet, z. B. bgb, owig_1968
  abbr TEXT NOT NULL,                         -- Zitierkürzel (amtabk), z. B. BGB, OWiG
  title TEXT NOT NULL,
  stand TEXT NOT NULL DEFAULT '',             -- standkommentar(e), z. B. „zuletzt geändert durch …“
  sha256 TEXT NOT NULL,                       -- Hash des XML: gleich → nichts zu tun
  fetched_at TEXT NOT NULL,
  pinned INTEGER NOT NULL DEFAULT 0           -- 1 = aus der Kernliste, 0 = nachgeladen
);
CREATE UNIQUE INDEX IF NOT EXISTS module_legal_laws_abbr ON module_legal_laws(abbr);

CREATE TABLE IF NOT EXISTS module_legal_norms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  law_key TEXT NOT NULL REFERENCES module_legal_laws(key),
  abbr TEXT NOT NULL,
  enbez TEXT NOT NULL,                        -- „§ 536c“, „Art 3“
  doknr TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  gliederung TEXT NOT NULL DEFAULT '',
  text TEXT NOT NULL,
  position INTEGER NOT NULL,
  valid_from TEXT NOT NULL,                   -- Abrufzeitpunkt dieser Fassung
  valid_to TEXT                               -- NULL = gültig; sonst ersetzt am …
);
CREATE INDEX IF NOT EXISTS module_legal_norms_lookup ON module_legal_norms(abbr, enbez, valid_to);
CREATE INDEX IF NOT EXISTS module_legal_norms_law ON module_legal_norms(law_key, valid_to);

CREATE VIRTUAL TABLE IF NOT EXISTS module_legal_norms_fts USING fts5(
  abbr, enbez, title, gliederung, text,
  content='module_legal_norms', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS module_legal_norms_ai AFTER INSERT ON module_legal_norms BEGIN
  INSERT INTO module_legal_norms_fts(rowid, abbr, enbez, title, gliederung, text)
  VALUES (new.id, new.abbr, new.enbez, new.title, new.gliederung, new.text);
END;
CREATE TRIGGER IF NOT EXISTS module_legal_norms_ad AFTER DELETE ON module_legal_norms BEGIN
  INSERT INTO module_legal_norms_fts(module_legal_norms_fts, rowid, abbr, enbez, title, gliederung, text)
  VALUES ('delete', old.id, old.abbr, old.enbez, old.title, old.gliederung, old.text);
END;

CREATE TABLE IF NOT EXISTS module_legal_sync (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  state TEXT NOT NULL,                        -- running | done | failed
  laws_total INTEGER NOT NULL DEFAULT 0,
  laws_changed INTEGER NOT NULL DEFAULT 0,
  errors TEXT NOT NULL DEFAULT '[]'           -- JSON-Liste {key, error}
);
