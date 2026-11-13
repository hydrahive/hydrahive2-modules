-- TV-Werkstatt Entrümpeln Teil 1: zuletzt gelesener Stand je Fernseher (Kennung + Pakete an/aus), nur lesend erhoben.
CREATE TABLE IF NOT EXISTS module_tvwerkstatt_debloat_reads (
    device_id  TEXT PRIMARY KEY REFERENCES module_tvwerkstatt_devices(device_id) ON DELETE CASCADE,
    ident      TEXT NOT NULL,                        -- JSON: brand, product, device, model, build_id, incremental
    packages   TEXT NOT NULL,                        -- JSON: {paket: "on"|"off"}
    commit_id  TEXT NOT NULL,                        -- Stand der Listen (cleanyourtv)
    read_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
