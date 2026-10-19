import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { Costs } from "./Costs"
import { HowTo } from "./HowTo"
import { HOWTO } from "./guideLogic"
import { firstVisit, nextWorkspace, stepOf } from "./guideLogic"
import { studioI18n } from "./i18n"
import { WorkspaceIntro } from "./WorkspaceIntro"
import { WORKSPACES } from "./workspaces"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const s = (lang: "de" | "en") => studioI18n[lang].studio as unknown as Record<string, unknown> & Record<string, Record<string, unknown>>

describe("C3 – Reihenfolge der Arbeit", () => {
  it("Schritt X von 6 und der nächste Reiter", () => {
    expect([...WORKSPACES]).toEqual(["plan", "generate", "edit", "audio", "subtitles", "deliver"])
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

describe("C3 – die Anleitung nennt nur Knöpfe, die es wirklich gibt", () => {
  it("jedes zitierte „…“ in „So geht’s“ ist ein Text der Oberfläche (de und en)", () => {
    for (const lang of ["de", "en"] as const) {
      const all: string[] = []
      const walk = (v: unknown) => { if (typeof v === "string") all.push(v); else if (v && typeof v === "object") Object.values(v).forEach(walk) }
      const st = s(lang)
      walk(Object.fromEntries(Object.entries(st).filter(([k]) => k !== "howto" && k !== "howto_more")))
      const texts = all.map((x) => x.replace(/\{\{[^}]+\}\}/g, "…"))
      const steps = JSON.stringify([st.howto, st.howto_more])
      const quoted = [...steps.matchAll(lang === "de" ? /„([^“]+)“/g : /“([^”]+)”/g)].map((m) => m[1])
      const unknown = quoted.filter((q) => !texts.some((x) => x === q || x === `${q} …` || x.replace(" …", "") === q.replace(" …", "")))
      expect(unknown, lang).toEqual([])
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
      for (const w of WORKSPACES) expect(ws[w], `${lang} ws.${w}`).toBeTruthy()
    }
  })
})

type El = { props: Record<string, unknown> & { children?: unknown } }
const find = (node: unknown, attr: string, out: El[] = []): El[] => {
  if (Array.isArray(node)) node.forEach((n) => find(n, attr, out))
  else if (node && typeof node === "object" && "props" in node) {
    const el = node as El
    if (el.props[attr] !== undefined) out.push(el)
    find(el.props.children, attr, out)
  }
  return out
}

describe("C3 – Klicks führen an die richtige Stelle", () => {
  it("„Weiter zu …“ öffnet den nächsten Reiter", () => {
    const onGo = vi.fn()
    const tree = WorkspaceIntro({ workspace: "audio", open: true, onToggle: noop, onGo })
    ;(find(tree, "data-intro-next")[0].props.onClick as () => void)()
    expect(onGo).toHaveBeenCalledWith("subtitles")
  })
  it("jeder Schritt in „So geht’s“ springt in seinen Reiter", () => {
    const onGo = vi.fn()
    const tree = HowTo({ onGo })
    for (const b of find(tree, "data-howto-go")) (b.props.onClick as () => void)()
    expect(onGo.mock.calls.map((c) => c[0])).toEqual(HOWTO.map((h) => h.ws))
  })
})

describe("C3 – Modell im Kosten-Hinweis kommt aus dem Drehbuch", () => {
  it("Shot-Formular reicht Bild-, Video- und Sprachmodell weiter", async () => {
    const { ShotForm } = await import("./ShotForm")
    const shot = { id: "s", shot: "", prompt: "", element_ids: [], duration: 5, status: "image_ready", image_rel: "a.png", video_rel: null, variants: ["a.png"], speech: "Hallo" }
    const out = html(<ShotForm shot={shot as never} index={0} elements={[]} presets={[]} busy={false} onSave={noop} onDelete={noop} base="/w"
      onGenerate={noop} onChoose={noop} onVideo={noop} onSpeech={noop} models={{ image: "m/bild", video: "m/video", voice: "m/stimme" }} />)
    for (const m of ["m/bild", "m/video", "m/stimme"]) expect(out).toContain(`costs_hint:{"model":"${m}"}`)
  })
  it("Planen gibt die Modelle des Drehbuchs an das Shot-Formular", () => {
    const src = Object.values(import.meta.glob("./PlanInspector.tsx", { query: "?raw", import: "default", eager: true })).join("")
    expect(src).toMatch(/<ShotForm[\s\S]*models=\{plan\.screenplay\.models\}/)
  })
})

describe("C3 – im Studio verdrahtet", () => {
  it("Kurzhilfe bekommt den Reiterwechsel; Hilfe öffnet sich beim ersten Besuch", () => {
    const src = Object.values(import.meta.glob(["./StudioPage.tsx", "./useStudioState.ts"], { query: "?raw", import: "default", eager: true })).join("\n")
    expect(src).toMatch(/<WorkspaceIntro[^>]*onGo=\{s\.setWorkspace\}/)
    expect(src).toMatch(/useState<"help" \| "command" \| null>\(\(\) => \(firstVisit\(\) \? "help" : null\)\)/)
  })
})
