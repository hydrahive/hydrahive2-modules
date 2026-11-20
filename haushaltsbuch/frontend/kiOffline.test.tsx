// KI-Ausfall bei Kategorie-Vorschlägen (Till 20.11.2026): Hinweis statt Fehler.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: {}, buildErrorMessage: () => "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
import { KI_OFFLINE_TEXT, KiOfflineHint } from "./ImportBatchView"
import type { ImportBatch } from "./types"

describe("KI nicht erreichbar", () => {
  it("Hinweis nennt Historie und Handarbeit, als Status (kein Fehler)", () => {
    const html = renderToStaticMarkup(<KiOfflineHint />)
    expect(html).toContain("KI nicht erreichbar")
    expect(html).toContain("Historie")
    expect(html).toContain('role="status"')
    expect(KI_OFFLINE_TEXT).toContain("von Hand")
  })
  it("Antwortfeld ist typisiert", () => {
    const b = { suggestion_notice: "llm_unavailable" } as Pick<ImportBatch, "suggestion_notice">
    expect(b.suggestion_notice).toBe("llm_unavailable")
  })
})
