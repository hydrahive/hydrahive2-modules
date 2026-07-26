CREATE TABLE IF NOT EXISTS module_mediacenter_jobs (
    result_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    media_type TEXT NOT NULL CHECK(media_type IN ('movie','tv','book','audiobook','audioplay','music')),
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('available','claimed_prewrite','submitting','uncertain','consumed','manual_review_required','expired')),
    claim_token TEXT,
    handoff_id TEXT NOT NULL UNIQUE,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
    sab_job_id TEXT UNIQUE,
    error_code TEXT,
    action_expires_at TEXT NOT NULL,
    state_changed_at TEXT NOT NULL,
    submitting_at TEXT,
    uncertain_until TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK(state != 'consumed' OR sab_job_id IS NOT NULL),
    CHECK(state NOT IN ('submitting','uncertain') OR submitting_at IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_mediacenter_jobs_owner_state
    ON module_mediacenter_jobs(owner, state, updated_at);
