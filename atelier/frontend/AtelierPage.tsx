import { useEffect, useState, useCallback } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { atelierApi } from "./api"
import { CharacterLibrary } from "./CharacterLibrary"
import { GeneratePanel } from "./GeneratePanel"
import { Gallery } from "./Gallery"
import { VideoPanel } from "./VideoPanel"
import type { AtelierCharacter, AtelierCI, GalleryItem, PresetCatalog } from "./types"

const DEFAULT_CI: AtelierCI = { palette: [], style_anchor: "", default_model: "", aspect_ratio: "1:1" }

/** Atelier — Projekt-gebundene Media-Generierung mit Charakter-Konsistenz. */
export function AtelierPage() {
  const { t } = useTranslation("atelier")
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<string>("")
  const [ci, setCI] = useState<AtelierCI>(DEFAULT_CI)
  const [characters, setCharacters] = useState<AtelierCharacter[]>([])
  const [gallery, setGallery] = useState<GalleryItem[]>([])
  const [root, setRoot] = useState<string>("")
  const [presets, setPresets] = useState<PresetCatalog>({})
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [videoTick, setVideoTick] = useState(0)

  useEffect(() => {
    projectsApi.list().then((ps) => {
      setProjects(ps)
      if (ps.length > 0) setProjectId((cur) => cur || ps[0].id)
    })
    atelierApi.presets().then(setPresets).catch(() => setPresets({}))
  }, [])

  const reload = useCallback(async (pid: string) => {
    if (!pid) return
    const [meta, c, chars, gal] = await Promise.all([
      atelierApi.meta(pid),
      atelierApi.getCI(pid),
      atelierApi.listCharacters(pid),
      atelierApi.gallery(pid),
    ])
    setRoot(meta.root)
    setCI(c)
    setCharacters(chars)
    setGallery(gal)
  }, [])

  useEffect(() => {
    if (projectId) reload(projectId)
  }, [projectId, reload])

  const refAbsPath = useCallback(
    (rel: string) => (root ? `${root}/${rel}` : rel),
    [root],
  )

  function toggle(id: string) {
    setSelectedIds((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))
  }

  if (projects.length === 0) {
    return <div className="p-6 text-slate-400">{t("no_projects")}</div>
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center gap-3 px-4 py-3 border-b border-slate-700 bg-slate-900/60">
        <h1 className="text-lg font-semibold text-slate-100">🎨 {t("title")}</h1>
        <div className="ml-auto flex items-center gap-2">
          <label className="text-xs text-slate-400">{t("project")}</label>
          <select
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value)
              setSelectedIds([])
            }}
            className="text-sm px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </header>

      <div className="grid grid-cols-[280px_1fr_360px] gap-4 p-4 flex-1 overflow-auto">
        <section className="overflow-auto">
          <CharacterLibrary
            projectId={projectId}
            characters={characters}
            selectedIds={selectedIds}
            onToggle={toggle}
            onChanged={() => reload(projectId)}
            refAbsPath={refAbsPath}
          />
        </section>
        <section className="overflow-auto">
          <GeneratePanel
            projectId={projectId}
            ci={ci}
            characters={characters}
            selectedIds={selectedIds}
            presets={presets}
            onGenerated={() => reload(projectId)}
          />
        </section>
        <section className="overflow-auto flex flex-col gap-3">
          <Gallery
            projectId={projectId}
            items={gallery}
            characters={characters}
            onPromoted={() => reload(projectId)}
            onVideoStarted={() => setVideoTick((n) => n + 1)}
          />
          <VideoPanel key={`${projectId}-${videoTick}`} projectId={projectId} refAbsPath={refAbsPath} />
        </section>
      </div>
    </div>
  )
}
