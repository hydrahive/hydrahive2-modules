ALTER TABLE module_ticket_github_links ADD COLUMN remote_title TEXT NOT NULL DEFAULT '';
ALTER TABLE module_ticket_github_links ADD COLUMN remote_body TEXT NOT NULL DEFAULT '';
ALTER TABLE module_ticket_github_links ADD COLUMN remote_state TEXT;
ALTER TABLE module_ticket_github_links ADD COLUMN remote_labels_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE module_ticket_github_links ADD COLUMN remote_assignees_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE module_ticket_github_links ADD COLUMN remote_updated_at TEXT;

CREATE INDEX IF NOT EXISTS idx_ticket_github_links_external
    ON module_ticket_github_links (connection_id, owner, repository, issue_number);
CREATE INDEX IF NOT EXISTS idx_ticket_github_links_sync
    ON module_ticket_github_links (sync_state, updated_at);
