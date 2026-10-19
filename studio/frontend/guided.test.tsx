import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})), put: vi.fn(() => new Promise(() => {})) } }))
import { cardsOf, doneSteps, ideaBody, sceneFromText, sceneTextPatch, titleFrom } from "./neu/guidedLogic"
import { ReplaceDialog } from "./neu/ReplaceDialog"
import { IdeaCards } from "./neu/IdeaCards"
import { IdeaForm } from "./neu/IdeaForm"
import { studioI18n } from "./i18n"
import type { Plan, Scene, Shot } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const shot = (o: Partial<Shot> = {}): Shot => ({ id: "x1", order: 0, shot: "", prompt: "p", element_ids: [], duration: 5, status: "planned",
  image_rel: null, video_rel: null, variants: [], ...o })
const scene = (o: Partial<Scene> = {}): Scene => ({ id: "s1", title: "T", description: "", location: "", time_of_day: "", element_ids: [],
  dialogues: [], camera: {}, shots: [], ...o })
const plan = (scenes: Scene[]): Plan => ({ base: "/w", presets: {}, elements: [], scenes,
  screenplay: { title: "", logline: "", description: "", aspect_ratio: "16:9", default_duration: 5, models: {} as Plan["screenplay"]["models"],
    look: { style: "", palette: [] }, scene_order: scenes.map((s) => s.id) } })

describe("G1 – Logik", () => {
  it("Karten: Text = Beschreibung, sonst Titel; Reihenfolge des Plans", () => {
    const cards = cardsOf(plan([scene({ id: "a", title: "Wald", description: "Hydra wacht auf." }), scene({ id: "b", title: "Schnee" })]))
    expect(cards.map((c) => [c.id, c.text])).toEqual([["a", "Hydra wacht auf."], ["b", "Schnee"]])
    expect(cardsOf(null)).toEqual([])
  })

  it("Text ändern: Szene bekommt Beschreibung + Titel; genau ein Shot → dessen Bildbeschreibung mit", () => {
    expect(sceneTextPatch(scene({ shots: [shot()] }), "Hydra fliegt über den See.")).toEqual({
      scene: { description: "Hydra fliegt über den See.", title: "Hydra fliegt über den See" }, shot: { id: "x1", prompt: "Hydra fliegt über den See." } })
    const two = sceneTextPatch(scene({ shots: [shot(), shot({ id: "x2" })] }), "Neu")
    expect(two.shot).toBeNull()
    expect(sceneTextPatch(scene({ shots: [] }), "Neu").shot).toBeNull()
  })

  it("Titel: erste Wörter, ohne Satzzeichen am Ende, höchstens 60 Zeichen", () => {
    expect(titleFrom("Hydra wacht im Herbstwald auf. Goldene Blätter fallen.")).toBe("Hydra wacht im Herbstwald auf")
    expect(titleFrom("  ")).toBe("")
    expect(titleFrom("a".repeat(100)).length).toBe(60)
    expect(titleFrom("Eins, zwei, drei!")).toBe("Eins, zwei, drei")
  })

  it("Neue Szene: Szene + ein Shot mit dem Text", () => {
    expect(sceneFromText("Hydra winkt.")).toEqual({ scene: { title: "Hydra winkt", description: "Hydra winkt." }, shot: { prompt: "Hydra winkt." } })
  })

  it("Idee-Auftrag: ein Shot je Szene, Art und Länge; Länge als Sekunden", () => {
    expect(ideaBody("  Hydra  ", "trailer", 1)).toEqual({ idea: "Hydra", length: "60", style: "", kind: "trailer", shots_per_scene: 1 })
    expect(ideaBody("x", "music", 0).length).toBe("30")
    expect(ideaBody("x", "short", 2).length).toBe("120")
  })

  it("Haken: Idee = es gibt Szenen; Bilder = jede Szene hat ein Bild; Bewegung = jede hat Video", () => {
    expect(doneSteps(null)).toEqual({ 1: false, 2: false, 3: false, 4: false, 5: false })
    const p = plan([scene({ shots: [shot({ image_rel: "a.png" })] }), scene({ id: "s2", shots: [shot({ image_rel: "b.png", video_rel: "b.mp4" })] })])
    expect(doneSteps(p)).toMatchObject({ 1: true, 3: true, 4: false })
    expect(doneSteps(plan([scene({ shots: [] })]))).toMatchObject({ 1: true, 3: false, 4: false })
    expect(doneSteps(plan([]))[1]).toBe(false)
  })
})

describe("G1 – Oberfläche", () => {
  it("Idee-Formular: Frage, Art, Länge, Format; „Geschichte vorschlagen“ mit Zeichen „kostet“ erst mit Text", () => {
    const form = (idea: string, busy = false) => html(<IdeaForm idea={idea} kind="trailer" length={1} format="16:9" hasScenes={false} busy={busy}
      error={null} model="test/text" onIdea={noop} onKind={noop} onLength={noop} onFormat={noop} onRun={noop} onSelf={noop} />)
    const out = form("")
    expect(out).toContain("guided.idea_question")
    expect(buttons(out)).toEqual(["guided.example", "guided.kind.trailer", "guided.kind.explainer", "guided.kind.short", "guided.kind.music",
      "guided.len.0", "guided.len.1", "guided.len.2", "guided.format.wide", "guided.format.tall", "guided.suggest costs_badge", "guided.self"])
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-guided-suggest/)
    expect(form("Hydra")).not.toMatch(/<button[^>]*disabled=""[^>]*data-guided-suggest/)
    expect(out).toContain("costs_hint:{\"model\":\"test/text\"}")
    expect(form("Hydra", true)).toContain("guided.writing")
    expect(buttons(form("Hydra")).includes("guided.example")).toBe(false)              // Beispiel nur bei leerem Feld
  })

  it("Idee-Formular mit Szenen: „Neue Geschichte vorschlagen“, kein „Selbst schreiben“", () => {
    const out = html(<IdeaForm idea="x" kind="trailer" length={1} format="9:16" hasScenes busy={false} error="kaputt" model=""
      onIdea={noop} onKind={noop} onLength={noop} onFormat={noop} onRun={noop} onSelf={noop} />)
    expect(buttons(out)).toContain("guided.suggest_again costs_badge")
    expect(buttons(out)).not.toContain("guided.self")
    expect(out).toContain("kaputt")
    expect(out).toMatch(/data-guided-format="9:16"[^>]*aria-pressed="true"|aria-pressed="true"[^>]*data-guided-format="9:16"/)
  })

  it("Karten: nummeriert, Text änderbar, hoch/runter/löschen, „Szene hinzufügen“; Gespeichert-Anzeige", () => {
    const cards = [{ id: "a", text: "Eins" }, { id: "b", text: "Zwei" }]
    const out = html(<IdeaCards cards={cards} saved="a" busy={false} onText={noop} onMove={noop} onDelete={noop} onAdd={noop} />)
    expect(out).toContain('aria-label="guided.scene_n:{"n":1}"')
    expect(out).toContain(">Eins</textarea>")
    expect(buttons(out)).toEqual(["guided.add_scene"])                                  // Pfeile/Löschen nur mit aria-label
    expect(out.match(/aria-label="guided\.delete_scene"/g)?.length).toBe(2)
    expect(out).toMatch(/aria-label="guided\.up"[^>]*disabled=""|disabled=""[^>]*aria-label="guided\.up"/)
    expect(out.match(/guided\.saved/g)?.length).toBe(1)                                // nur an der gespeicherten Karte
    expect(out.indexOf("guided.saved")).toBeLessThan(out.indexOf('data-guided-card="b"'))
    expect(out).toContain("guided.story_title:{\"count\":2}")
  })

  it("Ersetzen-Dialog: drei klare Wege, kein Browser-Popup", () => {
    const out = html(<ReplaceDialog count={4} busy={false} onReplace={noop} onAppend={noop} onClose={noop} />)
    expect(buttons(out)).toEqual(["guided.replace_yes", "guided.replace_append", "cancel"])
    expect(out).toContain("guided.replace_text:{\"count\":4}")
  })

  it("Texte de/en vollständig, ohne Fachwörter Shot/Prompt/Baustein", () => {
    const de = (studioI18n.de.studio as unknown as { guided: Record<string, unknown> }).guided
    const en = (studioI18n.en.studio as unknown as { guided: Record<string, unknown> }).guided
    const keys = (o: Record<string, unknown>, p = ""): string[] => Object.entries(o).flatMap(([k, v]) => v && typeof v === "object" ? keys(v as Record<string, unknown>, `${p}${k}.`) : [`${p}${k}`])
    expect(keys(en).sort()).toEqual(keys(de).sort())
    const text = JSON.stringify(de)
    expect(text).not.toMatch(/\bShot|Prompt|Baustein|Spur\b/)
  })
})
