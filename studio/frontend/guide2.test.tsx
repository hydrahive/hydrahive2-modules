import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { Costs } from "./Costs"
import { HowTo, HOWTO } from "./HowTo"
import { firstVisit, nextWorkspace, stepOf } from "./guideLogic"
import { studioI18n } from "./i18n"
import { WorkspaceIntro } from "./WorkspaceIntro"
import { WORKSPACES } from "./workspaces"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const s = (lang: "de" | "en") => studioI18n[lang].studio as unknown as Record<string, unknown> & Record<string, Record<string, unknown>>

describe("C3 – Reihenfolge der Arbeit", () => {
  it("Schritt X von 6 und der nächste Reiter", () => {
    expect(WORKSPACES.map((w) => w.id)).toEqual(["plan", "generate", "edit", "audio", "subtitles", "deliver"])
    expect(stepOf("plan")).toBe(1)
    expect(stepOf("deliver")).toBe(6)
    expect(nextWorkspace("plan")).toBe("generate")
    expect(nextWorkspace("subtitles")).toBe("deliver")
    expect(nextWorkspace("deliver")).toBeNull()
  })

  it("Hilfe öffnet sich beim allerersten Besuch einmal von selbst", () => {
    const store = new Map<string, string>()
    const ls = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) }
    expect(firstVisit(ls)).toBe(true)
    expect(firstVisit(ls)).toBe(false)
    expect(firstVisit({ getItem: () => { throw new Error("gesperrt") }, setItem: noop })).toBe(false)   // ohne Speicher: nie aufdrängen
  })
})

describe("C3 – Kurzhilfe je Reiter", () => {
  it("„Schritt 2 von 6 – …“ und Knopf zum nächsten Reiter", () => {
    const onGo = vi.fn()
    const out = html(<WorkspaceIntro workspace="generate" open onToggle={noop} onGo={onGo} />)
    expect(out).toContain('intro_step:{"n":2,"total":6,"name":"ws.generate"}')
    expect(out).toMatch(/<button[^>]*data-intro-next="edit"[^>]*>.*intro_next:\{"name":"ws.edit"\}/s)
  })
  it("in „Ausgabe“ kein Weiter-Knopf", () => {
    expect(html(<WorkspaceIntro workspace="deliver" open onToggle={noop} onGo={noop} />)).not.toContain("data-intro-next")
  })
})

describe("C3 – „So geht’s“ vollständig", () => {
  it("alle 6 Reiter in der Reihenfolge + Figur mit Foto, Löschen, Dateien, Kosten", () => {
    expect(HOWTO.map((h) => h.ws)).toEqual(["plan", "plan", "plan", "generate", "generate", "edit", "audio", "subtitles", "deliver"])
    const out = html(<HowTo onGo={noop} />)
    for (const k of ["film", "photo", "shots", "images", "videos", "cut", "audio", "subtitles", "deliver"]) expect(out).toContain(`howto.${k}.title`)
    for (const k of ["delete", "files", "costs"]) expect(out).toContain(`howto_more.${k}.title`)
    expect((out.match(/data-howto-go=/g) || []).length).toBe(9)
  })
  it("Texte de/en für jeden Schritt", () => {
    for (const lang of ["de", "en"] as const) {
      const h = s(lang).howto as Record<string, { title: string; text: string }>
      const m = s(lang).howto_more as Record<string, { title: string; text: string }>
      for (const x of HOWTO) expect(h[x.key]?.title && h[x.key]?.text, `${lang} ${x.key}`).toBeTruthy()
      for (const k of ["delete", "files", "costs"]) expect(m[k]?.title && m[k]?.text, `${lang} ${k}`).toBeTruthy()
      expect(String(h.photo.text)).toMatch(lang === "de" ? /Foto/ : /photo/)
    }
  })
})

describe("C3 – Kosten am Knopf", () => {
  it("Zeichen „kostet“ mit Modell im Hinweis", () => {
    const out = html(<Costs model="openai/gpt-5-image" />)
    expect(out).toContain("costs_badge")
    expect(out).toContain('title="costs_hint:{&quot;model&quot;:&quot;openai/gpt-5-image&quot;}"'.replace(/&quot;/g, '"'))
    expect(html(<Costs model="" />)).toContain('costs_hint_default')
  })

  it("jeder Knopf, der Geld kostet, trägt das Zeichen", () => {
    const files = import.meta.glob(["./ShotImage.tsx", "./ShotVideo.tsx", "./ShotSpeech.tsx", "./FreeForm.tsx", "./MusicForm.tsx", "./HearDialog.tsx",
      "./TranslateDialog.tsx", "./BatchDialog.tsx", "./StoryboardPanel.tsx", "./IdeaForm.tsx"], { query: "?raw", import: "default", eager: true })
    for (const [name, src] of Object.entries(files)) expect(String(src), name).toContain("<Costs")
  })
})

describe("C3 – jeder Knopf hat einen Namen", () => {
  it("in allen Bausteinen: Text, aria-label oder title", () => {
    const files = import.meta.glob(["./*.tsx", "!./*.test.tsx"], { query: "?raw", import: "default", eager: true })
    const nameless: string[] = []
    for (const [name, raw] of Object.entries(files)) {
      const src = String(raw)
      for (const m of src.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)) {
        const [, attrs, body] = m
        const hasText = /\{t\(|\{[a-zA-Z.?]+\}|[A-Za-zÄÖÜäöüß]{2,}/.test(body.replace(/<[^>]+>/g, ""))
        if (!hasText && !/aria-label=|title=/.test(attrs)) nameless.push(`${name}: ${attrs.slice(0, 60)}`)
      }
    }
    expect(nameless).toEqual([])
  })
  it("Papierkorb der Zeitleiste sagt, dass die Datei bleibt", () => {
    for (const lang of ["de", "en"] as const) expect(String((s(lang).action as Record<string, string>).delete)).toMatch(lang === "de" ? /Datei bleibt/ : /file stays/)
  })
})

describe("C3 – Texte", () => {
  it("de/en vorhanden", () => {
    for (const lang of ["de", "en"] as const) {
      for (const k of ["intro_step", "intro_next", "costs_badge", "costs_hint", "costs_hint_default"]) expect(s(lang)[k], `${lang} ${k}`).toBeTruthy()
      const ws = s(lang).ws as Record<string, string>
      for (const w of WORKSPACES) expect(ws[w.id], `${lang} ws.${w.id}`).toBeTruthy()
    }
  })
})
