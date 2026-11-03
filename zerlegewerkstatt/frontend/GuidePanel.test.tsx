import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { guideDe } from "./i18n.guide.de"

function translated(key: string): unknown {
  const path = key.replace(/^guide\./, "").split(".")
  return path.reduce<unknown>((value, part) => (
    value && typeof value === "object" ? (value as Record<string, unknown>)[part] : undefined
  ), guideDe)
}

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => translated(key) ?? key }),
}))

import { GuidePanel } from "./GuidePanel"

describe("integrierte Benutzeranleitung", () => {
  it("zeigt Schnellstart und ausführliche Arbeitsanleitung direkt in der Werkstatt", () => {
    const html = renderToStaticMarkup(<GuidePanel />)

    expect(html).toContain("In sechs Schritten zum ersten Bericht")
    expect(html).toContain("Fall anlegen")
    expect(html).toContain("Datei aufnehmen")
    expect(html).toContain("Ausführliche Anleitung öffnen")
    expect(html).toContain("Router-Firmware untersuchen")
    expect(html).toContain("Windows-Programm auf lokale Kommunikation prüfen")
    expect(html).toContain("Android-App untersuchen")
    expect(html).toContain("Eigenen Netzwerk-Mitschnitt untersuchen")
    expect(html).toContain("Beobachtet")
    expect(html).toContain("Beleg-ID")
    expect(html).toContain("Die Werkstatt führt keine hochgeladene Datei aus")
    expect(html).toContain("<details")
  })
})
