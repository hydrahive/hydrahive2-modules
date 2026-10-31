-- Radiostream 0.2.3: Lautheit je Titel (LUFS), einmal gemessen. loudness_tried verhindert dauerndes Neumessen
-- nicht messbarer Titel. Additiv.
ALTER TABLE module_radiostream_tracks ADD COLUMN loudness_lufs REAL;
ALTER TABLE module_radiostream_tracks ADD COLUMN loudness_tried INTEGER NOT NULL DEFAULT 0;
