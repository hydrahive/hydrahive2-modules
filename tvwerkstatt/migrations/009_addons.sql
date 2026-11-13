-- TV-Werkstatt Zusätze: Rechte der gebauten App (aapt2, inkl. Bibliotheken), kommagetrennt, ohne android.permission.
ALTER TABLE module_tvwerkstatt_builds ADD COLUMN permissions TEXT NOT NULL DEFAULT '';
