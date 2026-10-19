// Bauplan L (lokal erzeugen): lokale Modelle kosten nichts – kein „kostet“-Zeichen, sondern „lokal“.
import { describe, expect, it, vi } from "vitest"
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { renderToStaticMarkup } from "react-dom/server"
import { Costs } from "./Costs"
import { isLocalModel } from "./localModel"

const html = (n: React.ReactElement) => renderToStaticMarkup(n)

describe("L2 – lokale Modelle kosten nichts", () => {
  it("erkennt lokale Bild- und Text-Modelle", () => {
    expect(isLocalModel("local:wks/flux2-klein-image")).toBe(true)
    expect(isLocalModel("ollama/gemma4:latest")).toBe(true)
    expect(isLocalModel("openai/gpt-5-image")).toBe(false)
    expect(isLocalModel("my-local:model")).toBe(false)
    expect(isLocalModel(undefined)).toBe(false)
    expect(isLocalModel("")).toBe(false)
  })
  it("lokal: Zeichen „lokal“ ohne Münze, Hinweis nennt das Modell", () => {
    const out = html(<Costs model="local:wks/flux2-klein-image" />)
    expect(out).toContain("costs_local_badge")
    expect(out).toContain("costs_local_hint")
    expect(out).not.toContain("costs_badge<")
    expect(out).toContain("data-local")
    expect(out).not.toContain("data-costs")
  })
  it("Anbieter: wie bisher „kostet“", () => {
    const out = html(<Costs model="openai/gpt-5-image" />)
    expect(out).toContain("costs_badge")
    expect(out).toContain("data-costs")
  })
})
