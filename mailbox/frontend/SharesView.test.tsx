import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), put: vi.fn(), delete: vi.fn(), post: vi.fn(), patch: vi.fn() } }))

const { AccountShares, shareOptions } = await import("./AccountShares")
import type { SharesInfo } from "./api"

const INFO: SharesInfo = {
  shares: [{ target: "project:p1", level: "read", name: "Recht", created_by: "till", created_at: "" }],
  projects: [{ id: "p1", name: "Recht" }, { id: "p2", name: "Steuer" }],
  audit: [{ at: "2026-10-23T21:00:00Z", username: "till", project_id: "p1", tool: "mailbox_read", message_id: 7, result: "ok" }],
}

describe("Freigaben im Kontodialog", () => {
  it("bietet nur noch nicht freigegebene Ziele an, Buddy zuerst", () => {
    expect(shareOptions(INFO, "Buddy").map((o) => o.target)).toEqual(["buddy", "project:p2"])
    expect(shareOptions({ ...INFO, shares: [] }, "Buddy").map((o) => o.target)).toEqual(["buddy", "project:p1", "project:p2"])
  })

  it("zeigt Freigaben, Auswahl und Protokoll", () => {
    const h = renderToStaticMarkup(<AccountShares accountId="a1" initial={INFO} />)
    expect(h).toContain('data-mbx-share="project:p1"')
    expect(h).toContain(">Recht<")
    expect(h).toContain('value="project:p2"')
    expect(h).not.toContain('value="project:p1"')
    expect(h).toContain("mailbox_read")
  })

  it("ohne Freigaben: Hinweis statt Liste, kein Protokoll", () => {
    const h = renderToStaticMarkup(<AccountShares accountId="a1" initial={{ shares: [], projects: [], audit: [] }} />)
    expect(h).not.toContain("data-mbx-share=")
    expect(h).not.toContain("<details")
  })
})

describe("Freigabe-Stufen und Agenten-Entwürfe", () => {
  it("jede Freigabe hat ihre Stufe auswählbar, neue Freigabe mit Stufenwahl", () => {
    const h = renderToStaticMarkup(<AccountShares accountId="a1" initial={{ ...INFO,
      shares: [{ ...INFO.shares[0], level: "draft" }] }} />)
    const sel = /<select[^>]*data-mbx-share-level="project:p1"[^>]*>([\s\S]*?)<\/select>/.exec(h)?.[1] ?? ""
    expect(sel).toMatch(/<option value="draft" selected="">/)
    expect(h).toContain('data-mbx-share-new-level="1"')
  })

  it("Entwurfsliste markiert Agenten-Entwürfe", async () => {
    const { DraftList } = await import("./DraftList")
    const base = { account_id: "a", to: "", cc: "", bcc: "", body: "", mode: "new" as const, ref_message: null,
      with_attachments: false, updated_at: "2026-10-23T20:00:00Z" }
    const h = renderToStaticMarkup(<DraftList onOpen={() => {}} drafts={[
      { ...base, id: "d1", subject: "Vom Agenten", by_agent: true }, { ...base, id: "d2", subject: "Von mir" }]} />)
    expect(h.match(/data-mbx-draft-agent="1"/g)?.length).toBe(1)
  })
})
