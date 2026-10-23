import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "T0K" }) } }))

const { MessageView } = await import("./MessageView")
const { MessageList } = await import("./MessageList")
const { FolderTree } = await import("./FolderTree")
import type { MailDetail, MailItem } from "./api"
import { EXPANDED_ACCOUNTS_KEY } from "./folderCollapse"

const MAIL: MailDetail = {
  id: 7, account: "till@example.net", account_id: "acc1", folder: "INBOX", folder_id: 3, folder_role: "inbox", seen: 1, flagged: 0, date: "2026-10-21T09:30:00Z", from_addr: "Kanzlei <post@k.example>",
  to_addr: "till@example.net", cc_addr: "", subject: "Re: Unterlagen", text: "Anbei die Unterlagen.", has_html: true,
  attachments: [{ index: 0, name: "logo.png", type: "image/png", size: 10, inline: true },
    { index: 1, name: "Vertrag.pdf", type: "application/pdf", size: 2048, inline: false }],
  deleted_on_server: 0, parse_error: "",
}
const view = (m: Partial<MailDetail> = {}, images = false) =>
  renderToStaticMarkup(<MessageView mail={{ ...MAIL, ...m }} images={images} onImages={() => {}} />)

describe("Lesebereich", () => {
  it("HTML nur im sandbox-iframe OHNE allow-scripts, ohne same-origin", () => {
    const h = view()
    const iframe = /<iframe[^>]*>/.exec(h)?.[0] ?? ""
    expect(iframe).toContain('sandbox="allow-popups allow-popups-to-escape-sandbox"')
    expect(iframe).not.toContain("allow-scripts")
    expect(iframe).not.toContain("allow-same-origin")
    expect(iframe.toLowerCase()).toContain('referrerpolicy="no-referrer"')
  })

  it("Bilder erst nach Klick: Adresse ohne images, Knopf da; danach mit images=1, Knopf weg", () => {
    const before = view()
    expect(before).toContain("/api/modules/mailbox/messages/7/html?token=T0K\"")
    expect(before).toContain('data-mbx-images="1"')
    const after = view({}, true)
    expect(after).toContain("/api/modules/mailbox/messages/7/html?token=T0K&amp;images=1")
    expect(after).not.toContain('data-mbx-images="1"')
  })

  it("nur echte Anhänge als Download, Inline-Logo nicht", () => {
    const h = view()
    expect(h).toContain('data-mbx-attachment="1"')
    expect(h).not.toContain('data-mbx-attachment="0"')
    expect(h).toContain("Vertrag.pdf")
  })

  it("Text-Mail ohne iframe, Text als Text", () => {
    const h = view({ has_html: false, text: "<script>alert(1)</script>" })
    expect(h).not.toContain("<iframe")
    expect(h).not.toContain("<script>")
    expect(h).toContain("&lt;script&gt;")
  })

  it("Hinweis bei nur noch im Archiv", () => {
    expect(view({ deleted_on_server: 1 })).toContain('data-mbx-archived="1"')
    expect(view()).not.toContain("data-mbx-archived")
  })

  it("Betreff mit HTML wird nie als HTML ausgegeben", () => {
    const h = view({ subject: "<img src=x onerror=alert(1)>" })
    expect(h).not.toContain("<img src=x")
  })
})

const ITEM: MailItem = { id: 1, account_id: "a", account: "till@example.net", folder: "INBOX", folder_id: 3,
  date: "2015-01-05T10:00:00Z", from_addr: "Anna <a@x.de>", to_addr: "", subject: "Hallo", snippet: "Text", seen: 0,
  flagged: 1, has_attachments: true, deleted_on_server: 1, thread_key: "" }

describe("Mailliste", () => {
  it("ungelesen fett, Symbole, mehr laden nur wenn mehr da ist", () => {
    const h = renderToStaticMarkup(<MessageList items={[ITEM]} total={5} selected={null} onSelect={() => {}} onMore={() => {}} showAccount />)
    expect(h).toContain("font-bold")
    expect(h).toContain('aria-label="markiert"')
    expect(h).toContain('aria-label="Anhang"')
    expect(h).toContain('aria-label="nur im Archiv"')
    expect(h).toContain('data-mbx-more="1"')
    expect(h).toContain("till@example.net · Text")
    const all = renderToStaticMarkup(<MessageList items={[ITEM]} total={1} selected={null} onSelect={() => {}} onMore={() => {}} showAccount={false} />)
    expect(all).not.toContain("data-mbx-more")
    expect(all).not.toContain("till@example.net ·")
  })

  it("leer", () => {
    expect(renderToStaticMarkup(<MessageList items={[]} total={0} selected={null} onSelect={() => {}} onMore={() => {}} showAccount={false} />)).toContain("Keine Mails")
  })
})

describe("Ordnerleiste", () => {
  const folders = [
    { id: 1, account_id: "a", account: "t@x.de", name: "INBOX", role: "inbox", total: 3, unread: 2, gone: 0 },
    { id: 2, account_id: "a", account: "t@x.de", name: "Alt", role: "", total: 1, unread: 0, gone: 1 },
    { id: 3, account_id: "a", account: "t@x.de", name: "Newsletter", role: "", total: 9, unread: 7, gone: 0 },
  ]

  it("startet eingeklappt, blendet Ordner aus und zählt nur ungelesene Posteingänge", () => {
    const h = renderToStaticMarkup(<FolderTree accounts={[]} selection={{ kind: "all" }} onSelect={() => {}} onAddAccount={() => {}} onSync={() => {}}
      folders={folders} />)
    expect(h).toContain('data-mbx-account-toggle="a"')
    expect(h).toContain('aria-expanded="false"')
    expect(h).not.toContain("data-mbx-folder")
    expect(h).toMatch(/Alle Posteingänge<\/span><span[^>]*>2</) // nur Posteingänge, nicht „Newsletter“ (7)
  })

  it("zeigt die Ordner eines im Browser aufgeklappt gespeicherten Kontos, aber keine weggefallenen", () => {
    vi.stubGlobal("localStorage", { getItem: (key: string) => key === EXPANDED_ACCOUNTS_KEY ? '["a"]' : null })
    try {
      const h = renderToStaticMarkup(<FolderTree accounts={[]} selection={{ kind: "all" }} onSelect={() => {}} onAddAccount={() => {}} onSync={() => {}}
        folders={folders} />)
      expect(h).toContain('aria-expanded="true"')
      expect(h).toContain('data-mbx-folder="1"')
      expect(h).toContain('data-mbx-folder="3"')
      expect(h).not.toContain('data-mbx-folder="2"')
      expect(h).toContain("Posteingang")
    } finally {
      vi.unstubAllGlobals()
    }
  })
})

describe("Ordnerleiste – Abgleich", () => {
  it("zeigt Fortschritt und Fehler des Kontos", () => {
    const acc = { id: "a", label: "Yahoo", address: "t@x.de", status: "error", status_detail: "Verbindung abgebrochen",
      sync: { running: 1, messages_done: 2200, folders_done: 0, folders_total: 9, finished_at: null, last_error: "" } }
    const h = renderToStaticMarkup(<FolderTree accounts={[acc as never]} selection={{ kind: "all" }} onSelect={() => {}}
      onAddAccount={() => {}} onSync={() => {}}
      folders={[{ id: 1, account_id: "a", account: "t@x.de", name: "INBOX", role: "inbox", total: 0, unread: 0, gone: 0 }]} />)
    expect(h).toContain("lädt … 2.200 Mails · Ordner 1/9")
    expect(h).toContain('data-mbx-status="1"')
    expect(h).toContain("animate-spin")
  })
})

