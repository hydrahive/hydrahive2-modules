CREATE TABLE IF NOT EXISTS module_mediacenter_results (
    result_id TEXT PRIMARY KEY
        CHECK(length(result_id) BETWEEN 20 AND 128)
        CHECK(result_id NOT GLOB '*[^A-Za-z0-9_-]*'),
    owner TEXT NOT NULL
        CHECK(length(owner) BETWEEN 1 AND 256),
    payload_json TEXT NOT NULL
        CHECK(length(payload_json) BETWEEN 2 AND 131072),
    expires_at REAL NOT NULL,
    claim_id TEXT UNIQUE
        CHECK(claim_id IS NULL OR length(claim_id) BETWEEN 20 AND 128)
        CHECK(claim_id IS NULL OR claim_id NOT GLOB '*[^A-Za-z0-9_-]*'),
    claim_expires_at REAL,
    selection_session_id TEXT
        CHECK(selection_session_id IS NULL OR length(selection_session_id) <= 512),
    created_at REAL NOT NULL,
    CHECK((claim_id IS NULL) = (claim_expires_at IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_mediacenter_results_owner_expiry
    ON module_mediacenter_results(owner, expires_at);
CREATE INDEX IF NOT EXISTS idx_mediacenter_results_claim_expiry
    ON module_mediacenter_results(claim_expires_at)
    WHERE claim_id IS NOT NULL;
