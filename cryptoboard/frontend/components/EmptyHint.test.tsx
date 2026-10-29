// Task 0dda5420: Leer-Zustände im Cryptoboard zeigen das eigene Hydra-Bild des Moduls.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { EmptyHint } from "./EmptyHint"

const VIEWS = join(__dirname, "..", "views")

describe("EmptyHint", () => {
  it("Bild als Deko + Text", () => {
    const html = renderToStaticMarkup(<EmptyHint text="Noch keine Bestände" />)
    expect(html).toMatch(/<img[^>]*src="[^"]*leer[^"]*\.webp"[^>]*alt=""/)
    expect(html).toContain("Noch keine Bestände")
  })
  it.each([
    ["AlertsView.tsx", "al_empty"], ["AnalyticsView.tsx", "an_empty"], ["PortfolioView.tsx", "pf_empty"],
    ["TradeLogView.tsx", "tx_empty"], ["DashboardView.tsx", "watchlist_empty"], ["WalletsView.tsx", "wl_empty"],
  ])("%s zeigt %s über EmptyHint", (file, key) => {
    const src = readFileSync(join(VIEWS, file), "utf8")
    expect(src).toMatch(new RegExp(`<EmptyHint text=\\{[^}]*t\\("${key}"\\)`))
    expect(src).not.toMatch(new RegExp(`<p[^>]*>\\{t\\("${key}"\\)\\}</p>`))
  })
  it("das Bild liegt im Modul", () => {
    expect(readFileSync(join(__dirname, "..", "assets", "leer.webp")).length).toBeGreaterThan(1000)
  })
})
