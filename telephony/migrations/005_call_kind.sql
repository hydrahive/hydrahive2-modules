-- Anrufart je Anruf (Till 25.10.2026): greeting = Ansage, assistant = Gespräch mit dem Assistenten, '' = nicht angenommen.
ALTER TABLE module_telephony_calls ADD COLUMN kind TEXT NOT NULL DEFAULT '';
