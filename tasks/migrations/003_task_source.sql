-- Herkunft eines Tasks (Task ef94594a): woraus er entstanden ist, zum Beispiel aus einer Idee.
-- source_kind nennt die Art ('idea'), source_id die ID dort. Beide leer bei von Hand angelegten Tasks.
-- Gesetzt wird die Herkunft nur vom anlegenden Modul, nicht über die Routen des Tasks-Moduls.
ALTER TABLE module_tasks ADD COLUMN source_kind TEXT;
ALTER TABLE module_tasks ADD COLUMN source_id TEXT;
