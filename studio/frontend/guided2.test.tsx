import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})), put: vi.fn(() => new Promise(() => {})) } }))
import { castState, castOpen, doneSteps } from "./neu/guidedLogic"
import { PersonCard } from "./neu/PersonCard"
import { CastIntro } from "./neu/StepCastLive"
import type { Job, Plan, PlanElement, Scene } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const el = (o: Partial<PlanElement> = {}): PlanElement => ({ id: "e1", kind: "character", name: "Hydra", description: "fünf Köpfe", style_anchor: "",
  palette: [], references: [], probe_rel: "", approved: false, no_photo: false, ...o })
const job = (o: Partial<Job>): Job => ({ id: "j", kind: "probe", target: "e1", scene_id: "", status: "running", error: null, result: null,
  created_at: "2026-10-19T10:00:00Z", finished_at: null, ...o })
const scene: Scene = { id: "s1", title: "T", description: "", location: "", time_of_day: "", element_ids: [], dialogues: [], camera: {}, shots: [] }
const plan = (elements: PlanElement[], scenes: Scene[] = [scene]): Plan => ({ base: "/w", presets: {}, elements, scenes,
  screenplay: { title: "", logline: "", description: "", aspect_ratio: "16:9", default_duration: 5, models: {} as Plan["screenplay"]["models"],
    look: { style: "", palette: [] }, scene_order: scenes.map((s) => s.id) } })
const card = (e: PlanElement, jobs: Job[] = [], uploading = false) => html(<PersonCard el={e} base="/w" jobs={jobs} uploading={uploading} busy={false} imageModel="m/bild"
  onName={noop} onDescription={noop} onPhoto={noop} onProbe={noop} onApprove={noop} onReopen={noop} onNoPhoto={noop} onOtherPhoto={noop} onDelete={noop} onRedescribe={noop} />)

describe("G2 – Logik", () => {
  it("Zustand einer Figur: leer → läuft → Probe → passt; ohne Foto; Fehler", () => {
    expect(castState(el(), [])).toBe("empty")
    expect(castState(el({ references: ["a.png"] }), [])).toBe("photo")                        // Foto da, noch kein Probebild
    expect(castState(el({ references: ["a.png"] }), [job({})])).toBe("busy")
    expect(castState(el({ probe_rel: "studio/media/probes/p.png" }), [])).toBe("probe")
    expect(castState(el({ probe_rel: "studio/media/probes/p.png", approved: true }), [])).toBe("approved")
    expect(castState(el({ no_photo: true }), [])).toBe("no_photo")
    expect(castState(el({ no_photo: true }), [job({})])).toBe("busy")
    expect(castState(el({ references: ["a.png"] }), [job({ status: "failed", error: "no_key" })])).toBe("failed")
    expect(castState(el({ references: ["a.png"] }), [job({ target: "anderer" })])).toBe("photo")    // fremder Auftrag zählt nicht
    expect(castState(el({ references: ["a.png"] }), [job({ kind: "image" })])).toBe("photo")
    expect(castState(el({ approved: true }), [])).toBe("empty")                                    // Freigabe ohne Probebild zählt nicht
    // ein altes fehlgeschlagenes Probebild verdeckt kein fertiges
    expect(castState(el({ probe_rel: "p.png" }), [job({ status: "failed", error: "no_key" })])).toBe("probe")
    // der jüngste Auftrag zählt
    expect(castState(el({ references: ["a.png"] }), [job({ status: "failed", created_at: "2026-10-19T09:00:00Z" }),
      job({ status: "running", created_at: "2026-10-19T11:00:00Z" })])).toBe("busy")
  })

  it("offen = weder passt noch ohne Foto; Haken Schritt 2", () => {
    const ok = el({ probe_rel: "p", approved: true })
    expect(castOpen([ok, el({ id: "e2", no_photo: true }), el({ id: "e3" })])).toBe(1)
    expect(doneSteps(plan([ok, el({ id: "e2", no_photo: true })]))[2]).toBe(true)
    expect(doneSteps(plan([ok, el({ id: "e3" })]))[2]).toBe(false)
    expect(doneSteps(plan([]))[2]).toBe(true)                                                     // ohne Figuren reicht die Geschichte
    expect(doneSteps(plan([], []))[2]).toBe(false)
  })
})

describe("G2 – Oberfläche", () => {
  it("leere Figur: Foto-Feld (ziehen/klicken), „Kein Foto“, Löschen", () => {
    const out = card(el())
    expect(out).toContain("guided.photo_drop")
    expect(out).toContain('accept=".png,.jpg,.jpeg,.webp,.gif"')
    expect(buttons(out)).toContain("guided.no_photo:{\"what\":\"guided.the_character\"}")
    expect(out).toContain('aria-label="guided.delete_entry:{"name":"Hydra"}"')
  })

  it("Foto da, noch kein Probebild: Foto zu sehen, Feld zum Tauschen, „Probebild zeigen“ (kostet)", () => {
    const out = card(el({ references: ["fotos/h.png"] }))
    expect(out).toContain('src="/f/w/fotos/h.png"')
    expect(out).toContain("guided.photo_drop")
    expect(buttons(out)).toContain("guided.probe_show costs_badge")
    expect(buttons(card(el()))).not.toContain("guided.probe_show costs_badge")                   // ohne Foto noch nicht
  })

  it("läuft: Wartehinweis, keine Knöpfe zum Freigeben", () => {
    const out = card(el({ references: ["fotos/h.png"] }), [job({})])
    expect(out).toContain("guided.probe_busy")
    expect(buttons(out)).not.toContain("guided.approve")
    expect(card(el(), [], true)).toContain("guided.uploading")
  })

  it("Probebild: Foto + Probebild nebeneinander, „Passt“, „Anderes Probebild“ (kostet), „Anderes Foto“", () => {
    const out = card(el({ references: ["fotos/h.png"], probe_rel: "studio/media/probes/p.png" }))
    expect(out).toContain('src="/f/w/fotos/h.png"')
    expect(out).toContain('src="/f/w/studio/media/probes/p.png"')
    expect(out).toContain("guided.probe_caption:{\"name\":\"Hydra\"}")
    expect(buttons(out)).toEqual(expect.arrayContaining(["guided.approve", "guided.probe_again costs_badge", "guided.other_photo"]))
    expect(out).toContain("costs_hint:{\"model\":\"m/bild\"}")
  })

  it("passt: grüne Bestätigung + „Ändern“", () => {
    const out = card(el({ references: ["fotos/h.png"], probe_rel: "p.png", approved: true }))
    expect(out).toContain("guided.approved_text:{\"name\":\"Hydra\"}")
    expect(buttons(out)).toContain("guided.change")
    expect(buttons(out)).not.toContain("guided.approve")
  })

  it("ohne Foto: Beschreibung sichtbar, „Probebild zeigen“, „Doch ein Foto“", () => {
    const out = card(el({ no_photo: true }))
    expect(out).toContain("guided.invents:{\"what\":\"guided.the_character\"}")
    expect(out).toContain(">fünf Köpfe</textarea>")
    expect(buttons(out)).toEqual(expect.arrayContaining(["guided.probe_show costs_badge", "guided.photo_after_all"]))
    const place = card(el({ kind: "place", no_photo: true }))
    expect(place).toContain("guided.invents:{\"what\":\"guided.the_place\"}")
  })

  it("Fehler am Probebild ist an der Karte zu lesen + neu versuchen", () => {
    const out = card(el({ references: ["fotos/h.png"] }), [job({ status: "failed", error: "no_key" })])
    expect(out).toContain("job_err.no_key")
    expect(buttons(out)).toContain("guided.probe_retry costs_badge")
  })

  it("Kopf: Namen aus der Geschichte, Anzahl offen, Knöpfe zum Hinzufügen", () => {
    const out = html(<CastIntro names={["Hydra", "Herbstwald"]} open={2} onAdd={noop} />)
    expect(out).toContain("guided.cast_found:{\"names\":\"Hydra, Herbstwald\"}")
    expect(buttons(out)).toEqual(["guided.add_character", "guided.add_place"])
    expect(html(<CastIntro names={[]} open={0} onAdd={noop} />)).toContain("guided.cast_none")
  })
})
