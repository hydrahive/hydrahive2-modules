// C2 – Oberfläche: Schalter „Autor darf die Gliederung direkt ändern“ und Kasten „Umbau-Vorschlag“ (Spec §2b).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { GHOST_EMPTY, type Book } from "../model"
import type { RestructureProposal } from "../restructure"
import type { BookState } from "../useBook"
import { RestructureProposalBox } from "./RestructureProposalBox"
import { StructureSwitch } from "./StructureSwitch"

const state = (p: Partial<BookState> = {}) => ({
  projectId: "p", canWrite: true, book: { id: "b", ghost: { ...GHOST_EMPTY } } as Book, change: vi.fn(), ...p,
} as unknown as BookState)
const proposal = (p: Partial<RestructureProposal> = {}): RestructureProposal => ({
  steps: [], lines: ["Kapitel „Anfang“ umbenennen in „Der Anfang“", "Neues Kapitel „Epilog“ mit 1 Szene(n)"],
  before: ["Anfang", "Mitte"], after: ["Der Anfang", "Mitte", "Epilog"], base_structure_version: 3, source: "agent",
  author: "Buch — Autor", note: "", session_id: "", at: "t", ...p,
})
const plain = (h: string) => h.replace(/&quot;/g, '"')

describe("StructureSwitch", () => {
  it("aus = Vorschlag (Standard), an = direkt", () => {
    expect(renderToStaticMarkup(<StructureSwitch state={state()} />)).not.toMatch(/<input[^>]*checked/)
    const on = state({ book: { id: "b", ghost: { ...GHOST_EMPTY, agent_structure: "direct" } } as Book })
    expect(renderToStaticMarkup(<StructureSwitch state={on} />)).toMatch(/<input[^>]*checked/)
  })
  it("Leser sehen den Schalter gesperrt", () => {
    expect(renderToStaticMarkup(<StructureSwitch state={state({ canWrite: false })} />)).toMatch(/<fieldset[^>]*disabled=""/)
  })
})

describe("RestructureProposalBox", () => {
  it("zeigt Schritte, Vorher (Weggefallenes durchgestrichen) und Nachher (Neues markiert), Übernehmen/Verwerfen", () => {
    const html = renderToStaticMarkup(<RestructureProposalBox state={state()} proposal={proposal()} />)
    expect(html).toContain("<li>Kapitel „Anfang“ umbenennen in „Der Anfang“</li>")
    expect(html).toMatch(/<li class="[^"]*line-through[^"]*">Anfang<\/li>/)
    expect(html).toMatch(/<li class="">Mitte<\/li>/)
    expect(html).toMatch(/<li>Epilog<span[^>]*>struct_proposal_new<\/span><\/li>/)
    expect(html).toContain(">struct_apply<")
    expect(html).toContain(">struct_reject<")
  })
  it("Hinweis des Agenten und „ersetzt …“", () => {
    const html = plain(renderToStaticMarkup(<RestructureProposalBox state={state()}
      proposal={proposal({ note: "Tempo", replaced_from: { author: "Buch — Struktur", at: "t0" } })} />))
    expect(html).toContain('proposal_note:{"note":"Tempo"}')
    expect(html).toContain('struct_proposal_replaced:{"who":"Struktur"}')
  })
  it("Leser: keine Knöpfe", () => {
    const html = renderToStaticMarkup(<RestructureProposalBox state={state({ canWrite: false })} proposal={proposal()} />)
    expect(html).not.toContain("struct_apply")
  })
})
