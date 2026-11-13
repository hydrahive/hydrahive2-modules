-- TV-Werkstatt Baustein 5: welcher Startbildschirm gerade Home ist (gelesen beim Prüfen, neben dem Original).
ALTER TABLE module_tvwerkstatt_devices ADD COLUMN current_home TEXT NOT NULL DEFAULT '';
