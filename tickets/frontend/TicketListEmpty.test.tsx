// Task 0dda5420: Die leere Ticket-Liste zeigt das eigene Hydra-Bild des Moduls statt des Inbox-Symbols.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = readFileSync(join(__dirname, "TicketList.tsx"), "utf8")

describe("TicketList leer", () => {
  it("zeigt das Leer-Bild des Moduls als Deko", () => {
    expect(SRC).toMatch(/import leerBild from "\.\/assets\/leer\.webp"/)
    expect(SRC).toMatch(/<img src=\{leerBild\} alt=""/)
  })
  it("kein Inbox-Symbol mehr im Leer-Zustand (im Listenkopf bleibt es)", () => {
    const leer = SRC.slice(SRC.indexOf("tickets.length === 0"), SRC.indexOf('t("emptyHint")'))
    expect(leer).not.toMatch(/<Inbox /)
    expect(leer).toContain("leerBild")
  })
  it("Texte bleiben", () => {
    expect(SRC).toContain('t("empty")')
    expect(SRC).toContain('t("emptyHint")')
  })
  it("das Bild liegt im Modul", () => {
    expect(readFileSync(join(__dirname, "assets", "leer.webp")).length).toBeGreaterThan(1000)
  })
})
