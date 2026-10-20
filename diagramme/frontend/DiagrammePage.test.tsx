import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), delete: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (f: (s: unknown) => unknown) => f({ token: "t", username: "till", role: "admin" }) }))
import { DiagrammePage } from "./DiagrammePage"
import { PurgeDialog } from "./PurgeDialog"
import { Tile } from "./Tile"

const ITEM = { id: "d_1", title: "Ablauf der Websuche", kind: "workflow", project_id: "p", project_name: "Hydrahive DEV",
  created_at: "2026-10-20T16:03:23Z", versions: 2, username: "till", deleted_at: null, preview_state: "ok", version_of: null }

describe("Seite Diagramme", () => {
  it("zeigt Kopf mit Suche, Projekt-Auswahl und Papierkorb", () => {
    const html = renderToStaticMarkup(<DiagrammePage />)
    expect(html).toContain("title")
    expect(html).toContain("search_placeholder")
    expect(html).toContain("all_projects")
    expect(html).toContain("trash")
  })

  it("Admin sieht den Kasten für alle Agenten", () => {
    expect(renderToStaticMarkup(<DiagrammePage />)).toContain("agents_title")
  })

  it("Kachel: Titel, Art in Worten, Projekt, Fassungen – kein Fachwort", () => {
    const html = renderToStaticMarkup(<Tile item={ITEM} onOpen={() => {}} />)
    expect(html).toContain("Ablauf der Websuche")
    expect(html).toContain("kind.workflow")
    expect(html).toContain("Hydrahive DEV")
    expect(html).toContain("versions_count:{&quot;count&quot;:2}")
  })

  it("Endgültig-löschen-Dialog ist ein eigener Dialog mit klarer Warnung", () => {
    const html = renderToStaticMarkup(<PurgeDialog title="Ablauf" busy={false} onConfirm={() => {}} onClose={() => {}} />)
    expect(html).toContain('role="dialog"')
    expect(html).toContain("purge_question")
    expect(html).toContain("purge_confirm")
  })
})
