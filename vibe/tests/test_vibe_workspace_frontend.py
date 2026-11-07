from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend"
ERRORS = (
    "vibe_workspace_unavailable",
    "vibe_workspace_conflict",
    "vibe_workspace_migration_failed",
)


def test_workspace_fehler_sind_im_chat_und_in_beiden_sprachen_erklaert() -> None:
    workspace = (ROOT / "Workspace.tsx").read_text(encoding="utf-8")
    translations = (ROOT / "i18n.ts").read_text(encoding="utf-8")

    for code in ERRORS:
        assert code in workspace
        assert translations.count(code) == 2, code


def test_allgemeine_vibe_fehlerliste_kennt_workspace_fehler() -> None:
    page = (ROOT / "VibePage.tsx").read_text(encoding="utf-8")
    translations = (ROOT / "i18n.ts").read_text(encoding="utf-8")

    for code in (*ERRORS, "vibe_container_remove_failed"):
        assert code in page
        assert translations.count(code) == 2, code
