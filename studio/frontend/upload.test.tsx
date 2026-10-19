import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), postForm: vi.fn(() => new Promise(() => {})) } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { ElementForm } from "./ElementForm"
import { LibraryPanel } from "./LibraryPanel"
import type { PlanElement } from "./planApi"
import { acceptFor, filesFromDrop, isFileDrag, uploadSummary, type UploadResult } from "./uploadLogic"

const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const noop = () => {}
const EL: PlanElement = { id: "e1", kind: "character", name: "Ole", description: "", style_anchor: "", palette: [], references: ["studio/media/uploads/a.png"] }
const ok = (name: string): UploadResult => ({ ok: true, name, kind: "image", rel: `studio/media/uploads/${name}`, size: 10 })
const bad = (name: string, error: string): UploadResult => ({ ok: false, name, error })

describe("7a – Hochladen (rein)", () => {
  it("Dateiauswahl: Bibliothek nimmt Bild, Video, Ton; Referenz nur Bilder", () => {
    expect(acceptFor("library")).toContain(".png")
    expect(acceptFor("library")).toContain(".mp4")
    expect(acceptFor("library")).toContain(".mp3")
    expect(acceptFor("reference")).toContain(".jpg")
    expect(acceptFor("reference")).not.toContain(".mp4")
  })
  it("Ziehen aus dem Dateimanager erkennen, Ziehen aus der Bibliothek nicht", () => {
    expect(isFileDrag({ types: ["Files"] })).toBe(true)
    expect(isFileDrag({ types: ["application/x-studio-media"] })).toBe(false)
    const f = new File(["x"], "a.png")
    expect(filesFromDrop({ files: [f] as unknown as FileList })).toEqual([f])
  })
  it("Rückmeldung: alles gut / teils / Fehler je Datei mit Text", () => {
    expect(uploadSummary([ok("a.png"), ok("b.png")])).toEqual({ key: "upload_done", count: 2, failed: [] })
    const mixed = uploadSummary([ok("a.png"), bad("b.exe", "studio_upload_invalid")])
    expect(mixed).toEqual({ key: "upload_partly", count: 1, failed: [{ name: "b.exe", error: "studio_upload_invalid" }] })
    expect(uploadSummary([bad("x.png", "studio_upload_too_large")]).key).toBe("upload_failed")
  })
})

describe("7a – Bibliothek: Hochladen …", () => {
  const panel = (p: Partial<React.ComponentProps<typeof LibraryPanel>> = {}) => html(
    <LibraryPanel items={[]} loading={false} error={null} truncated={false} selected={null} onSelect={noop} onUpload={noop} uploading={false} {...p} />)
  it("Knopf mit Dateiauswahl (mehrere, passende Arten), Hinweis aufs Ablegen", () => {
    const out = panel()
    expect(out).toMatch(/<button[^>]*data-library-upload[^>]*>.*upload_open/)
    expect(out).toMatch(/<input[^>]*type="file"[^>]*multiple=""[^>]*accept="[^"]*\.png[^"]*\.mp4[^"]*"/)
    expect(out).toContain("upload_drop_hint")
  })
  it("während des Hochladens: gesperrt mit Hinweis", () => {
    const out = panel({ uploading: true })
    expect(out.match(/<button[^>]*data-library-upload[^>]*>/)?.[0]).toContain('disabled=""')
    expect(out).toContain("upload_running")
  })
  it("ohne Hochladen (z. B. nur Ansicht): kein Knopf", () => {
    expect(html(<LibraryPanel items={[]} loading={false} error={null} truncated={false} selected={null} onSelect={noop} />)).not.toContain("data-library-upload")
  })
})

describe("7a – Baustein: Referenzbild hochladen", () => {
  const form = (p: Partial<React.ComponentProps<typeof ElementForm>> = {}) =>
    html(<ElementForm element={EL} base="/w" images={[]} busy={false} onSave={noop} onDelete={noop} onUploadReference={noop} uploading={false} {...p} />)
  it("Knopf „Bild hochladen …“ mit Dateiauswahl nur für Bilder, Hinweis aufs Ablegen", () => {
    const out = form()
    expect(out).toMatch(/<button[^>]*data-element-upload[^>]*>.*upload_reference/)
    expect(out).toMatch(/<input[^>]*type="file"[^>]*accept="[^"]*\.png[^"]*"/)
    expect(out.match(/<input[^>]*type="file"[^>]*>/)?.[0]).not.toContain(".mp4")
    expect(out).toContain("upload_reference_hint")
  })
  it("auch ohne Bilder in der Bibliothek möglich; bei 8 Referenzen gesperrt; beim Hochladen gesperrt", () => {
    expect(form()).toContain("data-element-upload")
    const full = form({ element: { ...EL, references: Array.from({ length: 8 }, (_, i) => `r${i}.png`) } })
    expect(full.match(/<button[^>]*data-element-upload[^>]*>/)?.[0]).toContain('disabled=""')
    expect(full).toContain("upload_reference_full")
    expect(form({ uploading: true }).match(/<button[^>]*data-element-upload[^>]*>/)?.[0]).toContain('disabled=""')
  })
  it("Hochladen gibt die noch nicht gespeicherten Felder mit (sie werden zuerst gespeichert, nichts geht verloren)", async () => {
    const { pendingElement } = await import("./uploadLogic")
    expect(pendingElement(EL, { ...EL, name: "Ole Neu" }, "#111, #222")).toEqual({ kind: "character", name: "Ole Neu", description: "",
      style_anchor: "", palette: ["#111", "#222"], references: EL.references })
    expect(pendingElement(EL, EL, "")).toBeNull()                           // nichts geändert → nichts vorher speichern
  })
})

describe("7a – im Studio verdrahtet", () => {
  it("Planen reicht das Hochladen an den Baustein weiter (sonst fehlt der Knopf)", async () => {
    const files = import.meta.glob(["./StudioPage.tsx"], { query: "?raw", import: "default", eager: true })
    const src = Object.values(files)[0] as string
    const planning = src.match(/planning && !s\.item \? <PlanInspector[^>]*>/)?.[0] ?? ""
    expect(planning).toContain("upload={up}")
    expect(src).toMatch(/<LibraryPanel[^>]*onUpload=/)
  })
})
