import { describe, expect, it } from "vitest"
import { attachmentsTooBig, buildSendForm, draftKey, emptyDraft, fromPrefill, isDirty, MAX_ATTACH, needsConfirm, recipientsOk } from "./composeFormat"

describe("Schreibfenster-Logik", () => {
  it("Vorlage aus Antwort: Text = leer + Zitat darunter, Empfänger/Betreff übernommen", () => {
    const d = fromPrefill("acc1", "reply_all", 7, { to: "A <a@x.de>", cc: "b@x.de", subject: "Re: Hallo", quote: "> Hi", attachments: [] })
    expect(d).toMatchObject({ account_id: "acc1", mode: "reply_all", ref_message: 7, to: "A <a@x.de>", cc: "b@x.de", subject: "Re: Hallo" })
    expect(d.body).toBe("\n\n> Hi")
  })

  it("Weiterleiten: Anhänge des Originals standardmäßig mitnehmen, Empfänger leer", () => {
    const d = fromPrefill("acc1", "forward", 7, { to: "", cc: "", subject: "WG: x", quote: "---", attachments: ["a.pdf"] })
    expect(d.with_attachments).toBe(true)
    expect(d.to).toBe("")
  })

  it("Empfänger nötig – außer bei Antworten (Server kennt sie)", () => {
    expect(recipientsOk({ ...emptyDraft("a"), to: "" })).toBe(false)
    expect(recipientsOk({ ...emptyDraft("a"), bcc: "x@y.de" })).toBe(true)
    expect(recipientsOk({ ...emptyDraft("a"), mode: "reply", ref_message: 3 })).toBe(true)
    expect(recipientsOk({ ...emptyDraft("a"), mode: "forward", ref_message: 3 })).toBe(false)
  })

  it("Anhänge: Summe über 25 MB zu groß", () => {
    expect(attachmentsTooBig([{ size: MAX_ATTACH }])).toBe(false)
    expect(attachmentsTooBig([{ size: MAX_ATTACH - 1 }, { size: 2 }])).toBe(true)
  })

  it("Formular zum Senden: alle Felder, Anhänge als files, Entwurf-ID mit", () => {
    const f = buildSendForm({ ...emptyDraft("acc1"), to: "a@x.de", subject: "s", body: "b", mode: "forward", ref_message: 9,
      with_attachments: true }, [new File(["x"], "a.txt")], "d1")
    expect(f.get("account_id")).toBe("acc1")
    expect(f.get("ref_message")).toBe("9")
    expect(f.get("with_attachments")).toBe("true")
    expect(f.get("draft_id")).toBe("d1")
    expect((f.getAll("files")[0] as File).name).toBe("a.txt")
  })

  it("neue Mail: kein ref_message, kein draft_id im Formular", () => {
    const f = buildSendForm({ ...emptyDraft("acc1"), to: "a@x.de" }, [], null)
    expect(f.has("ref_message")).toBe(false)
    expect(f.has("draft_id")).toBe(false)
  })

  it("geändert = Inhalt anders als zuletzt gespeichert (für Auto-Speichern)", () => {
    const a = { ...emptyDraft("acc1"), body: "x" }
    expect(isDirty(a, a)).toBe(false)
    expect(isDirty({ ...a, body: "y" }, a)).toBe(true)
    expect(draftKey(a)).toBe(draftKey({ ...a }))
  })

  it("Löschen braucht Bestätigung, Markieren/Verschieben nicht", () => {
    expect(needsConfirm("delete")).toBe(true)
    for (const a of ["seen", "unseen", "flag", "unflag", "move"]) expect(needsConfirm(a)).toBe(false)
  })
})
