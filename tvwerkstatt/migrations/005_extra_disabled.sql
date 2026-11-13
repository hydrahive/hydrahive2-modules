-- TV-Werkstatt: was beim Aufspielen zusätzlich zum Original abgeschaltet wurde (Google TV: Einrichtungs-Helfer),
-- damit „Zurück zum Original“ es wieder einschaltet. Kommagetrennt, nur Paketnamen aus backend/guard.py.
ALTER TABLE module_tvwerkstatt_devices ADD COLUMN extra_disabled TEXT NOT NULL DEFAULT '';
