import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), postForm: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "T0K" }) } }))
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))

const { Composer, StatusLine } = await import("./Composer")
const { MessageActions } = await import("./MessageActions")
const { DraftList } = await import("./DraftList")
const { AccountSettings } = await import("./AccountSettings")
const { FolderTree } = await import("./FolderTree")
import type { Account, MailDetail, SavedDraft } from "./api"
import { emptyDraft } from "./composeFormat"
import type { FolderRow } from "./mailFormat"

const ACC = { id: "acc1", address: "till@example.net", sender_name: "Till" } as Account
const ACC2 = { id: "acc2", address: "t2@example.net", sender_name: "" } as Account
const MAIL = { id: 7, account: "till@example.net", account_id: "acc1", folder: "INBOX", folder_id: 3, folder_role: "inbox",
  seen: 1, flagged: 0, deleted_on_server: 0 } as MailDetail
const F = (id: number, account_id: string, name: string, role = "", gone = 0): FolderRow =>
  ({ id, account_id, account: "", name, role, total: 0, unread: 0, gone })
const FOLDERS = [F(3, "acc1", "INBOX", "inbox"), F(4, "acc1", "Projekte"), F(5, "acc2", "Fremd"), F(6, "acc1", "Alt", "", 1)]

const composer = (patch = {}, extra = {}) => renderToStaticMarkup(
  <Composer accounts={[ACC, ACC2]} initial={{ ...emptyDraft("acc1"), ...patch }} draftId={null} onClose={() => {}} {...extra} />)

describe("Schreibfenster", () => {
  it("Absenderkonten mit Namen; neue Mail: Konto wählbar", () => {
    const h = composer()
    expect(h).toContain("Till &lt;till@example.net&gt;")
    expect(h).toContain("t2@example.net")
    expect(/<select[^>]*data-mbx-from[^>]*>/.exec(h)?.[0]).not.toContain("disabled")
  })

  it("Antwort: Konto und Betreff fest (Unterhaltung + Absender bleiben richtig)", () => {
    const h = composer({ mode: "reply", ref_message: 7, subject: "Re: x" })
    expect(/<select[^>]*data-mbx-from[^>]*>/.exec(h)?.[0]).toContain("disabled")
    expect(/<input[^>]*data-mbx-field="subject"[^>]*>/.exec(h)?.[0]).toContain("disabled")
  })

  it("Cc/Bcc erst auf Klick – außer sie sind schon gefüllt", () => {
    expect(composer()).not.toContain('data-mbx-field="bcc"')
    expect(composer({ cc: "a@x.de" })).toContain('data-mbx-field="bcc"')
  })

  it("Weiterleiten: Häkchen für Original-Anhänge nur wenn es welche gibt", () => {
    expect(composer({ mode: "forward", ref_message: 7, with_attachments: true }, { originalAttachments: ["a.pdf"] }))
      .toContain("compose.withOriginal")
    expect(composer({ mode: "forward", ref_message: 7 })).not.toContain("compose.withOriginal")
  })

  it("Text als Text: Eingaben landen nie als HTML im Fenster", () => {
    const h = composer({ body: "<img src=x onerror=alert(1)>", subject: "<b>x</b>", to: "\"><script>" })
    expect(h).not.toContain("<img src=x")
    expect(h).not.toContain("<script>")
    expect(h).not.toContain("<b>x</b>")
  })
})

describe("Ergebniszeile", () => {
  const ok = (sent_copy: "server" | "provider" | "archive_only", more = {}) =>
    renderToStaticMarkup(<StatusLine status={{ kind: "sent", result: { sent: true, message_id: "<m>", refused: [], sent_copy, warning: "", ...more } }} />)

  it("je nach Ablage eigene Meldung; nur-Archiv als Hinweis (gelb)", () => {
    expect(ok("server")).toContain("compose.sent<")
    expect(ok("provider")).toContain("compose.sentProvider")
    expect(ok("archive_only")).toContain("compose.sentArchiveOnly")
    expect(ok("archive_only")).toContain("text-amber-200")
  })

  it("abgelehnte Adressen und Warnung werden gezeigt – als Text", () => {
    const h = ok("server", { refused: ["<img src=x>@x.de"], warning: "<b>w</b>" })
    expect(h).toContain("compose.refused")
    expect(h).not.toContain("<img src=x>")
    expect(h).not.toContain("<b>w</b>")
  })

  it("Fehlerart → eigener Text; Grenze eigener Text", () => {
    const err = (code: string) => renderToStaticMarkup(<StatusLine status={{ kind: "error", code }} />)
    expect(err("auth")).toContain("compose.error.auth")
    expect(err("rate_limited")).toContain("compose.rateLimited")
    expect(renderToStaticMarkup(<StatusLine status={{ kind: "invalid", reason: "size" }} />)).toContain("compose.tooBig")
    expect(renderToStaticMarkup(<StatusLine status={{ kind: "invalid", reason: "text" }} />)).toContain("compose.textTooLong")
  })
})

describe("Aktionen", () => {
  const acts = (m: Partial<MailDetail> = {}) =>
    renderToStaticMarkup(<MessageActions mail={{ ...MAIL, ...m }} folders={FOLDERS} onCompose={() => {}} onChanged={() => {}} />)

  it("Verschieben nur in Ordner desselben Kontos, nicht in den aktuellen, nicht in verschwundene", () => {
    const h = acts()
    expect(h).toContain(">Projekte<")
    expect(h).not.toContain(">Fremd<")
    expect(h).not.toContain(">Alt<")
    expect(h).not.toMatch(/<option value="INBOX"/)
  })

  it("im Papierkorb heißt Löschen „endgültig vom Server“", () => {
    expect(acts()).toContain("action.delete<")
    expect(acts({ folder_role: "trash" })).toContain("action.deleteForever")
  })

  it("nur im Archiv: Antworten ja, Server-Aktionen nein", () => {
    const h = acts({ deleted_on_server: 1 })
    expect(h).toContain('data-mbx-reply="reply"')
    expect(h).not.toContain('data-mbx-act="delete"')
    expect(h).toContain("action.archiveOnly")
  })

  it("gelesen/ungelesen und markieren schalten um", () => {
    expect(acts({ seen: 1 })).toContain("action.markUnread")
    expect(acts({ seen: 0 })).toContain("action.markRead")
    expect(acts({ flagged: 1 })).toContain("action.unflag")
  })
})

describe("Entwürfe", () => {
  it("Liste als Text, leer mit Hinweis", () => {
    const d = { id: "d1", subject: "<b>E</b>", to: "a@x.de", updated_at: "2026-10-21T09:00:00Z" } as SavedDraft
    const h = renderToStaticMarkup(<DraftList drafts={[d]} onOpen={() => {}} />)
    expect(h).toContain("&lt;b&gt;E&lt;/b&gt;")
    expect(renderToStaticMarkup(<DraftList drafts={[]} onOpen={() => {}} />)).toContain("drafts.empty")
  })
})

describe("Kontoeinstellungen", () => {
  it("Absendername und Signatur vorbelegt, als Text", () => {
    const a = { id: "acc1", address: "till@example.net", sender_name: "<b>Till</b>", signature: "Gruß\n<script>x</script>" } as Account
    const h = renderToStaticMarkup(<AccountSettings account={a} onClose={() => {}} onSaved={() => {}} />)
    expect(h).toContain('value="&lt;b&gt;Till&lt;/b&gt;"')
    expect(h).toContain("&lt;script&gt;x&lt;/script&gt;")
    expect(h).not.toContain("<script>x")
    expect(h).toContain('maxLength="5000"')
  })
})

describe("Ordnerbaum M2", () => {
  const acc = { id: "acc1", address: "till@example.net", label: "Privat", status: "ok", status_detail: "" } as Account
  const tree = (extra = {}) => renderToStaticMarkup(<FolderTree accounts={[acc]} folders={[F(3, "acc1", "INBOX", "inbox")]}
    selection={{ kind: "all" }} onSelect={() => {}} onAddAccount={() => {}} onSync={() => {}} {...extra} />)
  it("Entwürfe-Eintrag mit Anzahl; Einstellungen je Konto nur wenn verdrahtet", () => {
    expect(tree({ draftCount: 2 })).toContain('data-mbx-drafts="1"')
    expect(tree()).not.toContain("data-mbx-settings-open")
    expect(tree({ onSettings: () => {} })).toContain('data-mbx-settings-open="acc1"')
    expect(tree({ onSettings: () => {} })).toContain("settings.open")
  })
})
