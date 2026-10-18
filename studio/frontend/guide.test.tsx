import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { HowTo } from "./HowTo"
import { PlanOutline } from "./PlanOutline"
import { ProgressBar } from "./ProgressBar"
import { StartCard } from "./StartCard"
import { StoryboardPanel } from "./StoryboardPanel"
import { WorkspaceIntro } from "./WorkspaceIntro"
import { nextStep, startWorkspace, type Overview } from "./guideLogic"
import { studioI18n } from "./i18n"
import type { Plan, Scene } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const O = (p: Partial<Overview>): Overview => ({ scenes: 0, shots: 0, with_image: 0, with_video: 0, clips: 0, atelier: false, books: 0, ...p })
const scene = (p: Partial<Scene>): Scene => ({ id: "s1", title: "Hafen", description: "", location: "", time_of_day: "", element_ids: [],
  dialogues: [], camera: {}, shots: [], ...p })
const PLAN: Plan = { base: "/w", presets: {}, elements: [], scenes: [], screenplay: { title: "" } as Plan["screenplay"] }
/** Sichtbarer Text eines Knopfs (ohne Symbole) – so wie ein Mensch ihn liest. */
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)

describe("B1 – wohin zuerst, was als Nächstes", () => {
  it("Start-Reiter: ohne Planung Planen, mit Shots ohne Schnitt Erzeugen, sonst Schneiden; gemerkter Reiter gewinnt", () => {
    expect(startWorkspace(O({}), null)).toBe("plan")
    expect(startWorkspace(O({ scenes: 2 }), null)).toBe("plan")                    // Szenen, aber noch keine Shots
    expect(startWorkspace(O({ scenes: 1, shots: 3 }), null)).toBe("generate")
    expect(startWorkspace(O({ scenes: 1, shots: 3, clips: 2 }), null)).toBe("edit")
    expect(startWorkspace(O({ scenes: 1, shots: 3, clips: 2 }), "plan")).toBe("plan")
    expect(startWorkspace(O({}), "kaputt")).toBe("plan")                           // Unsinn im Speicher zählt nicht
    expect(startWorkspace(null, null)).toBe("plan")
  })

  it("Nächster Schritt: Shots → Bilder → Videos → Schnitt → fertig", () => {
    expect(nextStep(O({}))).toEqual({ step: "plan", workspace: "plan" })
    expect(nextStep(O({ scenes: 1 }))).toEqual({ step: "shots", workspace: "plan" })
    expect(nextStep(O({ scenes: 1, shots: 3, with_image: 1 }))).toEqual({ step: "images", workspace: "generate" })
    expect(nextStep(O({ scenes: 1, shots: 3, with_image: 3, with_video: 1 }))).toEqual({ step: "videos", workspace: "generate" })
    expect(nextStep(O({ scenes: 1, shots: 3, with_image: 3, with_video: 3 }))).toEqual({ step: "cut", workspace: "edit" })
    expect(nextStep(O({ scenes: 1, shots: 3, with_image: 3, with_video: 3, clips: 3 }))).toBeNull()
  })
})

describe("B1 – Startfeld und beschriftete Knöpfe", () => {
  it("Startfeld: „Selbst anfangen“ als Knopf, Atelier nur wenn es etwas gibt", () => {
    const out = html(<StartCard atelier={false} books={0} busy={false} onStart={noop} onImport={noop} onIdea={noop} onBook={noop} />)
    expect(out).toContain("start_title")
    expect(buttons(out)).toContain("start_self")
    expect(buttons(out)).not.toContain("start_atelier")
    expect(buttons(html(<StartCard atelier books={0} busy={false} onStart={noop} onImport={noop} onIdea={noop} onBook={noop} />))).toContain("start_atelier")
  })

  it("Gliederung: „+ Szene“, „+ Figur“, „+ Ort“, „+ Gegenstand“ mit Text", () => {
    const out = html(<PlanOutline plan={PLAN} preview={null} selection={null} onSelect={noop} onMove={noop} onAddScene={noop} onAddElement={noop} onImport={noop}
      books={0} onIdea={noop} onBook={noop} />)
    for (const k of ["add_scene_short", "add_character_short", "add_place_short", "add_object_short"]) expect(buttons(out)).toContain(k)
  })

  it("Storyboard: Szene ohne Shots zeigt zwei große Knöpfe; Leiste hat „+ Shot“ mit Text", () => {
    const out = html(<StoryboardPanel scene={scene({})} base="/w" selected={null} busy={null} onSelect={noop} onAdd={noop} onMove={noop} onDecompose={noop} />)
    expect(buttons(out)).toEqual(["shots_ai", "shots_self"])                          // leere Szene: zwei große Wege, keine Doppelung
    const some = html(<StoryboardPanel scene={scene({ shots: [{ id: "x", order: 0, shot: "", prompt: "p", element_ids: [], duration: 3, status: "planned",
      image_rel: null, video_rel: null, variants: [] }] })} base="/w" selected={null} busy={null} onSelect={noop} onAdd={noop} onMove={noop} onDecompose={noop} />)
    expect(buttons(some)).not.toContain("shots_ai")
    expect(buttons(some)).toContain("add_shot_short")
  })
})

describe("B1 – Kurzhilfe, Fortschritt, So geht’s", () => {
  it("Kurzhilfe je Reiter, einklappbar", () => {
    for (const ws of ["plan", "generate", "edit"] as const) {
      const out = html(<WorkspaceIntro workspace={ws} open onToggle={noop} />)
      expect(out).toContain(`intro.${ws}`)
      expect(out).toContain('aria-label="intro_hide"')
    }
    const closed = html(<WorkspaceIntro workspace="plan" open={false} onToggle={noop} />)
    expect(closed).not.toContain("intro.plan")
    expect(closed).toContain('aria-label="intro_show"')
  })

  it("Fortschritt: Zahlen und „Weiter“-Knopf; ohne Shots nichts; fertig ohne „Weiter“", () => {
    const out = html(<ProgressBar overview={O({ scenes: 1, shots: 4, with_image: 3, with_video: 1 })} onGo={noop} />)
    expect(out).toContain('progress_shots:{"count":4}')
    expect(out).toContain('progress_images:{"done":3,"total":4}')
    expect(out).toContain('progress_videos:{"done":1,"total":4}')
    expect(buttons(out)).toEqual(["next.images"])
    expect(html(<ProgressBar overview={O({})} onGo={noop} />)).toBe("")
    expect(buttons(html(<ProgressBar overview={O({ scenes: 1, shots: 1, with_image: 1, with_video: 1, clips: 1 })} onGo={noop} />))).toEqual([])
  })

  it("So geht’s: fünf Schritte mit Sprung-Knöpfen in die Reiter", () => {
    const out = html(<HowTo onGo={noop} />)
    expect([...out.matchAll(/data-howto-step="(\d)"/g)].map((m) => m[1])).toEqual(["1", "2", "3", "4", "5"])
    expect(buttons(out)).toEqual(["howto_go.plan", "howto_go.plan", "howto_go.generate", "howto_go.generate", "howto_go.edit"])
  })

  it("Texte: alle neuen Schlüssel in de und en, keine Etappen-Nummern in Nutzertexten", () => {
    for (const lang of ["de", "en"] as const) {
      const s = studioI18n[lang].studio as Record<string, unknown>
      for (const k of ["start_title", "start_self", "start_atelier", "add_scene_short", "add_shot_short", "shots_ai", "shots_self",
        "intro_hide", "intro_show", "progress_shots_one", "progress_shots_other", "progress_images", "progress_videos", "howto_title"]) expect(s[k], `${lang}:${k}`).toBeTruthy()
      expect(Object.keys(s.intro as object).sort()).toEqual(["audio", "deliver", "edit", "generate", "plan", "subtitles"])
      expect(Object.keys(s.next as object).sort()).toEqual(["cut", "images", "plan", "shots", "videos"])
      const all = JSON.stringify(s)
      expect(all).not.toMatch(/Etappe \d|stage \d/i)
    }
  })
})
