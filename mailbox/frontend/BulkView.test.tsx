import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), postForm: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "T0K" }) } }))
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))

const { BulkBar } = await import("./BulkBar")
const { MessageList } = await import("./MessageList")
import type { MailItem } from "./api"

const M = (id: number, extra: Partial<MailItem> = {}) => ({ id, account_id: "a", account: "a@x.de", folder: "INBOX", folder_id: 1,
  date: "2026-10-21T09:00:00Z", from_addr: "x@y.de", to_addr: "", subject: `S${id}`, snippet: "", seen: 1, flagged: 0,
  has_attachments: false, deleted_on_server: 0, thread_key: "", ...extra }) as MailItem
const bar = (items: MailItem[], sel: number[], busy = false) =>
  renderToStaticMarkup(<BulkBar items={items} selected={new Set(sel)} busy={busy} onAct={() => {}} onClear={() => {}} />)

describe("Sammel-Leiste", () => {
  it("unsichtbar ohne Auswahl, mit Anzahl bei Auswahl", () => {
    expect(bar([M(1)], [])).toBe("")
    expect(bar([M(1), M(2)], [1, 2])).toContain("bulk.selected:{&quot;n&quot;:2}")
  })

  it("gelesen/markieren je nach Auswahl; alle Aktionen da", () => {
    const h = bar([M(1, { seen: 0 }), M(2, { flagged: 1 })], [1, 2])
    expect(h).toContain("action.markRead")
    expect(h).toContain("action.flag<")
    for (const a of ["archive", "junk", "delete"]) expect(h).toContain(`data-mbx-bulk-act="${a}"`)
    expect(bar([M(1, { flagged: 1 })], [1])).toContain("action.unflag")
  })

  it("nur-Archiv-Mails: Hinweis; nur solche → Knöpfe aus", () => {
    const mixed = bar([M(1), M(2, { deleted_on_server: 1 })], [1, 2])
    expect(mixed).toContain("bulk.archiveOnly:{&quot;n&quot;:1}")
    expect(/data-mbx-bulk-act="delete"[^>]*>/.exec(mixed)?.[0] ?? "").not.toMatch(/ disabled=""/)
    const only = bar([M(2, { deleted_on_server: 1 })], [2])
    expect(/<button[^>]*data-mbx-bulk-act="delete"[^>]*>/.exec(only)?.[0] ?? "").toMatch(/ disabled=""/)
  })

  it("während der Aktion gesperrt", () => {
    expect(/<button[^>]*data-mbx-bulk-act="seen"[^>]*>/.exec(bar([M(1)], [1], true))?.[0] ?? "").toMatch(/ disabled=""/)
  })
})

describe("Liste mit Kästchen", () => {
  const list = (checked: number[], withCheck = true) => renderToStaticMarkup(<MessageList items={[M(1), M(2)]} total={2}
    selected={null} onSelect={() => {}} onMore={() => {}} showAccount={false} checked={new Set(checked)}
    {...(withCheck ? { onCheck: () => {}, onCheckAll: () => {} } : {})} />)
  it("je Mail ein Kästchen, angehakte sind an; „alle“ nur wenn alle an", () => {
    const h = list([1])
    expect(/<input[^>]*data-mbx-check="1"[^>]*>/.exec(h)?.[0]).toContain("checked")
    expect(/<input[^>]*data-mbx-check="2"[^>]*>/.exec(h)?.[0]).not.toContain("checked")
    expect(/<input[^>]*data-mbx-check-all[^>]*>/.exec(h)?.[0]).not.toContain("checked")
    expect(/<input[^>]*data-mbx-check-all[^>]*>/.exec(list([1, 2]))?.[0]).toContain("checked")
  })
  it("ohne Verdrahtung keine Kästchen (M1-Verhalten)", () => {
    expect(list([], false)).not.toContain("data-mbx-check")
  })
})
