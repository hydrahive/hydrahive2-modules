import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})) } }))
vi.mock("@/features/cockpit/CockpitShell", () => ({ CockpitShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }))
vi.mock("@/features/cockpit/CockpitTopbar", () => ({ CockpitTopbar: () => null }))
import { nav, routes } from "./index"
import { firstGuidedVisit } from "./neu/guidedLogic"
import { GuidedHelp } from "./neu/GuidedHelp"
import { StudioHeader } from "./StudioHeader"

const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const store = () => { const m = new Map<string, string>(); return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => { m.set(k, v) } } }

describe("G6 – Umstellen", () => {
  it("Wege: /studio = geführt, /studio/profi = Profi, /studio/neu leitet weiter; Menü zeigt /studio", () => {
    const paths = routes.map((r) => r.path)
    expect(paths).toEqual(["/studio", "/studio/profi", "/studio/neu"])
    expect((routes[0].element.type as { name: string }).name).toBe("GuidedPage")
    expect((routes[1].element.type as { name: string }).name).toBe("StudioPage")
    expect(nav.map((n) => n.path)).toEqual(["/studio"])
  })

  it("Profi-Ansicht: Knopf „Zum geführten Weg“ in der Kopfzeile", () => {
    const out = html(<StudioHeader projects={[]} projectId="" onProject={() => {}} onReload={() => {}} workspace="plan" onWorkspace={() => {}}
      onCommand={() => {}} onHelp={() => {}} />)
    expect(out).toMatch(/<a[^>]*href="\/studio"[^>]*>.*guided\.to_guided/s)
  })

  it("Profi-Hilfe geht nicht mehr von selbst auf; geführte Kurzhilfe einmal beim ersten Besuch", () => {
    const src = Object.values(import.meta.glob(["./useStudioState.ts"], { query: "?raw", import: "default", eager: true })).join("\n")
    expect(src).not.toMatch(/firstVisit\(\)/)                                            // Profi: kein Aufgehen von selbst
    const s = store()
    expect(firstGuidedVisit(s)).toBe(true)
    expect(firstGuidedVisit(s)).toBe(false)
    expect(firstGuidedVisit(undefined)).toBe(false)
  })

  it("Kurzhilfe: 5 Schritte in einfachen Sätzen, schließbar", () => {
    const out = html(<GuidedHelp onClose={() => {}} />)
    for (const n of [1, 2, 3, 4, 5]) expect(out).toContain(`guided.help.${n}`)
    expect(out).toContain("guided.help_title")
    expect(out).toContain("guided.help_close")
  })
})
