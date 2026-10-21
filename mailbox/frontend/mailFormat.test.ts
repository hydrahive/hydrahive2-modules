import { describe, expect, it } from "vitest"
import { accountState, folderLabel, groupFolders, senderName, shortDate, size, type FolderRow } from "./mailFormat"

const f = (id: number, account: string, name: string, role = ""): FolderRow =>
  ({ id, account_id: account, account: `${account}@x.de`, name, role, total: 0, unread: 0, gone: 0 })

describe("Mailbox-Anzeige", () => {
  it("Ordner je Konto, Posteingang zuerst, dann Rollen, dann alphabetisch", () => {
    const g = groupFolders([f(1, "b", "Zebra"), f(2, "a", "Sent", "sent"), f(3, "a", "INBOX", "inbox"), f(4, "a", "Ablage"),
      f(5, "a", "Trash", "trash"), f(6, "a", "Drafts", "drafts")])
    expect(g.map((x) => x.account)).toEqual(["a@x.de", "b@x.de"])
    expect(g[0].folders.map((x) => x.name)).toEqual(["INBOX", "Drafts", "Sent", "Trash", "Ablage"])
  })

  it("Rollen auf Deutsch, sonst Ordnername", () => {
    expect(folderLabel({ name: "INBOX", role: "inbox" })).toBe("Posteingang")
    expect(folderLabel({ name: "[Gmail]/Alle Nachrichten", role: "all" })).toBe("Alle Nachrichten")
    expect(folderLabel({ name: "Steuer 2019", role: "" })).toBe("Steuer 2019")
  })

  it("kurzes Datum: heute Uhrzeit, letzte Tage Wochentag, sonst Datum", () => {
    const now = new Date("2026-10-21T15:00:00")
    expect(shortDate("2026-10-21T07:15:00Z", now)).toMatch(/^\d{2}:\d{2}$/)
    expect(shortDate("2026-10-19T07:15:00Z", now)).toMatch(/^Mo/)
    expect(shortDate("2015-01-05T10:00:00Z", now)).toBe("05.01.2015")
    expect(shortDate("", now)).toBe("")
    expect(shortDate("kaputt", now)).toBe("")
  })

  it("Absendername", () => {
    expect(senderName("Anna Beispiel <anna@example.org>")).toBe("Anna Beispiel")
    expect(senderName('"Müller, Jürgen" <j@x.de>')).toBe("Müller, Jürgen")
    expect(senderName("<nur@adresse.de>")).toBe("nur@adresse.de")
    expect(senderName("plain@x.de")).toBe("plain@x.de")
    expect(senderName("")).toBe("(ohne Absender)")
  })

  it("Größe", () => {
    expect(size(500)).toBe("500 B")
    expect(size(20_480)).toBe("20 KB")
    expect(size(3_355_443)).toBe("3,2 MB")
  })

  it("Kontostatus", () => {
    expect(accountState("ok").tone).toBe("ok")
    expect(accountState("auth_failed")).toEqual({ text: "Anmeldung fehlgeschlagen", tone: "err" })
    expect(accountState("new").tone).toBe("warn")
  })
})
