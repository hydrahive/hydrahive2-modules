import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})) } }))
import { DraftPreview } from "./DraftPreview"
import { IdeaForm } from "./IdeaForm"
import { BookPick } from "./BookPick"
import { PlanOutline } from "./PlanOutline"
import { StartCard } from "./StartCard"
import { chosenScenes, draftCounts, ideaValid, toggleId } from "./draftLogic"
import type { Draft, DraftBook } from "./draftApi"
import type { Plan } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const PLAN: Plan = { base: "/w", presets: {}, elements: [], scenes: [], screenplay: { title: "" } as Plan["screenplay"] }
const DRAFT: Draft = {
  head: { title: "Licht im Sturm", logline: "Eine Wärterin hält das Licht.", description: "", style: "Noir" },
  elements: [{ key: "m", kind: "character", name: "Mira", description: "roter Mantel" }, { key: "t", kind: "place", name: "Leuchtturm", description: "" }],
  scenes: [
    { title: "Am Steg", description: "Mira wartet.", location: "Hafen", time_of_day: "Morgen", element_keys: ["m"],
      shots: [{ shot: "wide", prompt: "harbour", element_keys: ["m"], duration: 4 }, { shot: "", prompt: "face", element_keys: [], duration: 3 }] },
    { title: "Die Nacht", description: "", location: "", time_of_day: "", element_keys: ["t", "m"], shots: [] },
  ],
}
const BOOK: DraftBook = { id: "b1", title: "Der Leuchtturm", entities: 3,
  chapters: [{ id: "c1", title: "Ankunft", scenes: 2 }, { id: "c2", title: "Sturm", scenes: 1 }] }

describe("B2 – Wege ins Drehbuch", () => {
  it("Startfeld: „Aus einer Idee“ immer, „Aus dem Storyteller“ nur mit Büchern, Atelier nur mit Daten", () => {
    const base = { busy: false, onStart: noop, onImport: noop, onIdea: noop, onBook: noop }
    expect(buttons(html(<StartCard atelier={false} books={0} {...base} />))).toEqual(["start_idea", "start_self"])
    expect(buttons(html(<StartCard atelier books={2} {...base} />))).toEqual(["start_idea", "start_book", "start_self", "start_atelier"])
  })

  it("Gliederung: unter den Szenen „Szenen aus einer Idee“, mit Büchern auch „Aus dem Storyteller“", () => {
    const o = (books: number) => buttons(html(<PlanOutline plan={PLAN} preview={null} selection={null} onSelect={noop} onMove={noop}
      onAddScene={noop} onAddElement={noop} onImport={noop} books={books} onIdea={noop} onBook={noop} />))
    expect(o(0)).toContain("more_idea")
    expect(o(0)).not.toContain("more_book")
    expect(o(1)).toContain("more_book")
  })
})

describe("B2 – Aus einer Idee", () => {
  it("Formular: Idee, drei Längen, Stil; „Entwurf schreiben“ erst mit Idee", () => {
    const form = (idea: string) => html(<IdeaForm idea={idea} length="60" style="" busy={false} error={null}
      onIdea={noop} onLength={noop} onStyle={noop} onRun={noop} onClose={noop} />)
    const out = form("")
    expect(out).toContain("idea_label")
    expect(out).toContain("idea_style")
    expect(buttons(out)).toEqual(["idea_len.30", "idea_len.60", "idea_len.120", "cancel", "idea_run"])
    expect(out).toMatch(/aria-pressed="true"[^>]*>idea_len\.60|data-idea-length="60"[^>]*aria-pressed="true"/)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-idea-run/)
    expect(form("Ein Leuchtturm")).not.toMatch(/<button[^>]*disabled=""[^>]*data-idea-run/)
    expect(out).toContain("idea_cost")                                                  // Hinweis: ein KI-Aufruf
  })

  it("Während die KI schreibt: Hinweis, nichts anklickbar; Fehler wird gezeigt", () => {
    const busy = html(<IdeaForm idea="x" length="30" style="" busy error={null} onIdea={noop} onLength={noop} onStyle={noop} onRun={noop} onClose={noop} />)
    expect(busy).toContain("idea_busy")
    expect(busy).toMatch(/<button[^>]*disabled=""[^>]*data-idea-run/)
    const err = html(<IdeaForm idea="x" length="30" style="" busy={false} error="Fehlertext" onIdea={noop} onLength={noop} onStyle={noop} onRun={noop} onClose={noop} />)
    expect(err).toContain("Fehlertext")
  })

  it("Prüfung der Eingabe wie auf dem Server", () => {
    expect(ideaValid("", "")).toBe(false)
    expect(ideaValid("   ", "")).toBe(false)
    expect(ideaValid("x", "")).toBe(true)
    expect(ideaValid("x".repeat(2001), "")).toBe(false)
    expect(ideaValid("x", "s".repeat(301))).toBe(false)
  })
})

describe("B2 – Vorschau", () => {
  it("zeigt Titel, Mengen, Szenen mit Shots und Bausteinen; Übernehmen und Verwerfen", () => {
    const out = html(<DraftPreview draft={DRAFT} append={false} truncated={0} busy={false} canDecompose={false} decompose={false}
      onDecompose={noop} onApply={noop} onDiscard={noop} />)
    expect(out).toContain("Licht im Sturm")
    expect(out).toContain("Eine Wärterin hält das Licht.")
    expect(out).toContain('draft_counts:{"scenes":2,"shots":2,"elements":2}')
    expect(out).toContain("Am Steg")
    expect(out).toContain("Die Nacht")
    expect(out).toContain("harbour")
    expect(out).toContain("Mira")
    expect(out).toContain("Leuchtturm")
    expect(buttons(out)).toEqual(["draft_discard", "draft_apply"])
    const sceneTwo = out.split("Die Nacht")[1].split("</li>")[0]
    expect(sceneTwo).toContain("Leuchtturm, Mira")                                      // Bausteine der Szene in ihrer Zeile
    expect(out).toContain("draft_new")
    expect(out).not.toContain("draft_append")
  })

  it("Drehbuch hat schon Szenen → deutlicher Hinweis „wird angehängt“; abgeschnittene Szenen genannt", () => {
    const out = html(<DraftPreview draft={DRAFT} append truncated={5} busy={false} canDecompose={false} decompose={false}
      onDecompose={noop} onApply={noop} onDiscard={noop} />)
    expect(out).toContain("draft_append")
    expect(out).not.toContain("draft_new")
    expect(out).toContain('draft_truncated:{"count":5}')
  })

  it("Aus dem Storyteller (ohne Shots): Haken „Danach alle Szenen in Shots zerlegen“", () => {
    const props = { draft: DRAFT, append: false, truncated: 0, busy: false, onDecompose: noop, onApply: noop, onDiscard: noop }
    expect(html(<DraftPreview {...props} canDecompose={false} decompose={false} />)).not.toContain("draft_decompose")
    const out = html(<DraftPreview {...props} canDecompose decompose />)
    expect(out).toContain("draft_decompose")
    expect(out).toMatch(/<input[^>]*type="checkbox"[^>]*checked=""/)
  })

  it("Mengen", () => {
    expect(draftCounts(DRAFT)).toEqual({ scenes: 2, shots: 2, elements: 2 })
  })
})

describe("B2 – Aus dem Storyteller", () => {
  it("Buch wählen, Kapitel ankreuzen (Standard: alle), Zahl der Szenen", () => {
    const out = html(<BookPick books={[BOOK]} bookId="b1" chapters={["c1", "c2"]} busy={false} error={null}
      onBook={noop} onToggle={noop} onRun={noop} onClose={noop} />)
    expect(out).toContain("Der Leuchtturm")
    expect(out).toContain("Ankunft")
    expect(out).toContain("Sturm")
    expect((out.match(/type="checkbox"[^>]*checked=""/g) || []).length).toBe(2)
    expect(out).toContain('book_scenes:{"count":3}')
    expect(buttons(out)).toEqual(["cancel", "book_run"])
    const none = html(<BookPick books={[BOOK]} bookId="b1" chapters={[]} busy={false} error={null} onBook={noop} onToggle={noop} onRun={noop} onClose={noop} />)
    expect(none).toMatch(/<button[^>]*disabled=""[^>]*data-book-run/)                  // ohne Kapitel nichts zu übernehmen
    expect(html(<BookPick books={null} bookId="" chapters={[]} busy={false} error={null} onBook={noop} onToggle={noop} onRun={noop} onClose={noop} />)).toContain("loading")
    expect(html(<BookPick books={[]} bookId="" chapters={[]} busy={false} error={null} onBook={noop} onToggle={noop} onRun={noop} onClose={noop} />)).toContain("book_none")
  })

  it("Kapitel umschalten und gewählte Szenen zählen", () => {
    expect(toggleId(["c1", "c2"], "c1")).toEqual(["c2"])
    expect(toggleId(["c2"], "c1")).toEqual(["c2", "c1"])
    expect(chosenScenes(BOOK, ["c2"])).toBe(1)
    expect(chosenScenes(BOOK, ["c1", "c2"])).toBe(3)
    expect(chosenScenes(null, ["c1"])).toBe(0)
  })
})
