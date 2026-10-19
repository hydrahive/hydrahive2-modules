import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})), put: vi.fn(() => new Promise(() => {})) } }))
import { castToggle } from "./neu/guidedLogic"
import { ImageCard } from "./neu/ImageCard"
import { PersonCard } from "./neu/PersonCard"
import type { PlanElement, Shot } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const el = (o: Partial<PlanElement> = {}): PlanElement => ({ id: "h", kind: "character", name: "Hydra", description: "fünf bunte Köpfe", style_anchor: "",
  palette: [], references: ["fotos/h.png"], probe_rel: "studio/media/probes/p.png", approved: true, no_photo: false, ...o })
const shot = (o: Partial<Shot> = {}): Shot => ({ id: "x1", order: 0, shot: "", prompt: "Hydra erklärt", element_ids: ["h"], duration: 5, status: "planned",
  image_rel: "studio/media/images/a.png", variants: ["studio/media/images/a.png"], video_rel: null, cast: ["h"], ...o })

describe("H – Figur: Aussehen sichtbar und änderbar", () => {
  const card = (e: PlanElement) => html(<PersonCard el={e} base="/w" jobs={[]} uploading={false} busy={false} imageModel="m"
    onName={noop} onDescription={noop} onPhoto={noop} onProbe={noop} onApprove={noop} onReopen={noop} onNoPhoto={noop} onOtherPhoto={noop}
    onDelete={noop} onRedescribe={noop} />)

  it("bei jeder Figur mit Foto: „So sieht Hydra aus“ als Textfeld mit der Beschreibung", () => {
    for (const e of [el(), el({ approved: false }), el({ probe_rel: "", approved: false })]) {
      const out = card(e)
      expect(out).toContain('aria-label="guided.looks:{"name":"Hydra"}"')
      expect(out).toContain(">fünf bunte Köpfe</textarea>")
    }
  })

  it("mit Foto: „Aus dem Foto neu beschreiben“ (kostet kaum), ohne Foto nicht", () => {
    expect(buttons(card(el()))).toContain("guided.redescribe costs_badge")
    expect(buttons(card(el({ references: [], no_photo: true })))).not.toContain("guided.redescribe costs_badge")
  })
})

describe("H – Bild: nur angehakte, gezielt ändern", () => {
  const card = (s: Shot) => html(<ImageCard card={{ n: 1, part: 0, text: "Hydra erklärt", sceneId: "s1", shot: s }} base="/w" format="16:9"
    elements={[el(), el({ id: "b", name: "Buddy", references: [], probe_rel: "", approved: false })]} jobs={[]} busy={false} model="m"
    onMake={noop} onFlip={noop} onDrop={noop} onCast={noop} onChange={noop} />)

  it("„Mit dabei“ = genau die angehakten (cast vom Server)", () => {
    const out = card(shot())
    expect(out).toMatch(/aria-pressed="true"[^>]*>.*?Hydra/s)
    expect(out).toMatch(/aria-pressed="false"[^>]*>.*?Buddy/s)
  })

  it("mit Bild: Feld „Was soll anders sein?“ + „Bild ändern“ (kostet); „Anderes Bild machen“ bleibt", () => {
    const out = card(shot())
    expect(out).toContain('aria-label="guided.change_label"')
    expect(buttons(out)).toEqual(expect.arrayContaining(["guided.change_image costs_badge", "guided.another_image costs_badge"]))
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-guided-change/)                         // ohne Text gesperrt
  })

  it("ohne Bild: kein Ändern-Feld", () => {
    expect(card(shot({ image_rel: null, variants: [] }))).not.toContain("guided.change_label")
  })

  it("an/aus: weg = abgehakt (kein Ausschluss mehr nötig), dazu = angehakt", () => {
    expect(castToggle(shot({ element_ids: ["h", "b"], cast: ["h", "b"] }), "h")).toEqual({ element_ids: ["b"], excluded_ids: [] })
    expect(castToggle(shot({ element_ids: [], cast: [], excluded_ids: ["h"] }), "h")).toEqual({ element_ids: ["h"], excluded_ids: [] })
  })
})
