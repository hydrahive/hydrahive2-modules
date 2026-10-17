import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o && !("defaultValue" in o) ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { jobFor, jobText, runningJobs } from "./jobLogic"
import type { Job } from "./planApi"
import { ShotImage } from "./ShotImage"
import { StoryboardPanel } from "./StoryboardPanel"
import type { Scene, Shot } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const attr = (out: string, name: string) => [...out.matchAll(new RegExp(`${name}="([^"]+)"`, "g"))].map((m) => m[1])
const job = (p: Partial<Job>): Job => ({ id: "j", kind: "image", target: "a", scene_id: "s", status: "running", error: null, result: null, created_at: "2026-10-17T10:00:00Z", finished_at: null, ...p })
const shot = (id: string, p: Partial<Shot> = {}): Shot => ({ id, order: 0, shot: "", prompt: id, element_ids: [], duration: 5, status: "planned", image_rel: null, video_rel: null, variants: [], ...p })
const t = (k: string) => `T:${k}`

describe("Studio 3a – Bild erzeugen", () => {
  it("Logik: jüngster Auftrag je Shot, laufende zählen, Fehlertext aus dem Code", () => {
    const jobs = [job({ id: "neu", target: "a", status: "failed", error: "no_key", created_at: "2026-10-17T11:00:00Z" }),
      job({ id: "alt", target: "a", status: "done", created_at: "2026-10-17T10:00:00Z" }), job({ id: "b", target: "b", status: "running" })]
    expect(jobFor(jobs, "a")?.id).toBe("neu")
    expect(jobFor(jobs, "x")).toBeNull()
    expect(runningJobs(jobs)).toBe(1)
    expect(runningJobs([job({ status: "queued" }), job({ status: "running" }), job({ status: "done" })])).toBe(2)   // wartende zählen mit
    expect(jobText(t, job({ status: "failed", error: "no_key" }))).toBe("T:job_err.no_key")
    expect(jobText(t, job({ status: "failed", error: "irgendwas" }))).toBe("T:job_err.internal")
    expect(jobText(t, job({ status: "running" }))).toBe("")
  })

  it("Bildbereich: Knopf „Bild erzeugen“, ohne Bild ein Hinweis", () => {
    const out = html(<ShotImage shot={shot("a")} base="/w" job={null} onGenerate={noop} onChoose={noop} />)
    expect(out).toContain("data-shot-generate")
    expect(out).toContain("image_none")
    expect(out).not.toContain("data-shot-variant")
  })

  it("Bildbereich: läuft → gesperrt mit Ladeanzeige; Fehler → Meldung", () => {
    const running = html(<ShotImage shot={shot("a")} base="/w" job={job({ status: "running" })} onGenerate={noop} onChoose={noop} />)
    expect(running.match(/<button[^>]*data-shot-generate[^>]*>/)?.[0]).toContain(' disabled=""')
    expect(running).toContain("image_running")
    const failed = html(<ShotImage shot={shot("a")} base="/w" job={job({ status: "failed", error: "no_key" })} onGenerate={noop} onChoose={noop} />)
    expect(failed).toContain("data-shot-error")
    expect(failed).toContain("job_err.no_key")
    const old = html(<ShotImage shot={shot("a")} base="/w" job={job({ status: "done" })} onGenerate={noop} onChoose={noop} />)
    expect(old).not.toContain("data-shot-error")
  })

  it("Bildbereich: Varianten als Vorschaubilder, gewählte markiert, Bild über /api/files", () => {
    const s = shot("a", { image_rel: "studio/media/images/2.png", variants: ["studio/media/images/1.png", "studio/media/images/2.png"] })
    const out = html(<ShotImage shot={s} base="/w" job={null} onGenerate={noop} onChoose={noop} />)
    expect(attr(out, "data-shot-variant")).toEqual(["studio/media/images/1.png", "studio/media/images/2.png"])
    expect(out).toMatch(/data-shot-variant="studio\/media\/images\/2.png"[^>]*aria-pressed="true"/)
    expect(out).toContain("/api/files?path=%2Fw%2Fstudio%2Fmedia%2Fimages%2F2.png")
    expect(out).toContain("image_again")
  })

  it("Storyboard: Karte zeigt „läuft“ für Shots mit laufendem Auftrag", () => {
    const scene: Scene = { id: "s", title: "S", description: "", location: "", time_of_day: "", element_ids: [], dialogues: [], camera: {}, shots: [shot("a"), shot("b")] }
    const out = html(<StoryboardPanel scene={scene} base="/w" selected={null} busy={null} runningShots={["b"]} onSelect={noop} onAdd={noop} onMove={noop} onDecompose={noop} />)
    expect(attr(out, "data-storyboard-running")).toEqual(["b"])
  })
})

import { StudioHeader } from "./StudioHeader"

describe("Kopfzeile: echte Aufträge statt Beispiel", () => {
  const head = (running: number) => html(<StudioHeader projects={[]} projectId="" onProject={noop} onReload={noop} workspace="plan"
    onWorkspace={noop} onCommand={noop} onHelp={noop} running={running} />)
  it("zeigt die Zahl laufender Aufträge, ohne laufende nichts", () => {
    expect(head(3)).toContain('jobs:{"count":3}')
    expect(head(3)).toContain("data-studio-jobs")
    expect(head(0)).not.toContain("data-studio-jobs")
  })
})

import { studioI18n } from "./i18n"

describe("Bibliothek: Quelle „Studio“", () => {
  it("hat einen Namen in beiden Sprachen", () => {
    expect((studioI18n.de.studio.source as Record<string, string>).studio).toBe("Studio")
    expect((studioI18n.en.studio.source as Record<string, string>).studio).toBe("Studio")
  })
})

describe("Alte Shots ohne Varianten (vor 3a)", () => {
  it("Bildbereich stürzt nicht ab, zeigt das vorhandene Bild als einzige Wahl", () => {
    const old = { ...shot("a", { image_rel: "atelier/images/x.png" }), variants: undefined } as unknown as Shot
    const out = html(<ShotImage shot={old} base="/w" job={null} onGenerate={noop} onChoose={noop} />)
    expect(out).toContain("data-shot-generate")
    expect(attr(out, "data-shot-variant")).toEqual(["atelier/images/x.png"])
  })
})

import { PlanSidebar } from "./PlanSidebar"

describe("Planen, links: eindeutige Bereichs-Kennung", () => {
  it("Seitenleiste heißt „sidebar“, die Bibliothek darin bleibt „library“ – nie zweimal dieselbe", () => {
    const p = { plan: null, preview: null, selection: null, select: noop, error: null } as unknown as Parameters<typeof PlanSidebar>[0]["p"]
    const out = html(<PlanSidebar p={p} library={<section data-studio-panel="library" />} />)
    expect(attr(out, "data-studio-panel")).toEqual(["sidebar"])
  })
})
