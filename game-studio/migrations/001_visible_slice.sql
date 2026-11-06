-- Game Studio 0.1.0: per-user concept drafts for the early visible vertical slice.
CREATE TABLE IF NOT EXISTS module_game_studio_drafts (
    draft_id          TEXT PRIMARY KEY,
    owner_user_id     TEXT NOT NULL,
    entry_kind        TEXT NOT NULL CHECK (entry_kind IN ('new', 'adopt', 'archive')),
    title             TEXT NOT NULL,
    idea              TEXT NOT NULL DEFAULT '',
    genre             TEXT NOT NULL DEFAULT '',
    target_platform   TEXT NOT NULL DEFAULT 'desktop',
    core_action       TEXT NOT NULL DEFAULT '',
    success_condition TEXT NOT NULL DEFAULT '',
    current_step      INTEGER NOT NULL DEFAULT 1 CHECK (current_step BETWEEN 1 AND 5),
    revision          INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_module_game_studio_drafts_owner
    ON module_game_studio_drafts(owner_user_id, updated_at DESC);
