import { useEffect, useState, useCallback } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { HelpButton } from "@/i18n/HelpButton"
import { atelierApi } from "./api"
import { AudioPanel } from "./AudioPanel"
import { CharacterLibrary } from "./CharacterLibrary"
import { GeneratePanel } from "./GeneratePanel"
import { ImageGalleryPanel } from "./ImageGalleryPanel"
import { ClipLibraryPanel } from "./ClipLibraryPanel"
import { FilmComposerPanel } from "./FilmComposerPanel"
import { DirectorPanel } from "./DirectorPanel"
import { AtelierCutPanel } from "./AtelierCutPanel"
import type { AtelierCharacter, AtelierCI, AudioLibraryItem, GalleryItem, PresetCatalog, RepeatInput } from "./types"

const DEFAULT_CI: AtelierCI = { palette: [], style_anchor: "", default_model: "", aspect_ratio: "1:1" }
type AtelierTab = "characters" | "generate" | "gallery" | "clips" | "audio" | "films" | "cut" | "regie"

interface TabInfo {
  key: AtelierTab
  labelKey: string
  icon: string
  helpKey: string
}

const TABS: TabInfo[] = [
  { key: "characters", labelKey: "tab_characters", icon: "👥", helpKey: "tab_help_characters" },
  { key: "generate", labelKey: "tab_generate", icon: "✨", helpKey: "tab_help_generate" },
  { key: "gallery", labelKey: "tab_gallery", icon: "🖼️", helpKey: "tab_help_gallery" },
  { key: "clips", labelKey: "tab_clips", icon: "🎬", helpKey: "tab_help_clips" },
  { key: "audio", labelKey: "tab_audio", icon: "🎵", helpKey: "tab_help_audio" },
  { key: "films", labelKey: "tab_films", icon: "🎞️", helpKey: "tab_help_films" },
  { key: "cut", labelKey: "tab_cut", icon: "✂️", helpKey: "tab_help_cut" },
  { key: "regie", labelKey: "tab_regie", icon: "🎬", helpKey: "tab_help_regie" },
]

/** Atelier — Projekt-gebundene Media-Generierung mit Charakter-Konsistenz. */
export function AtelierPage() {
  const { t } = useTranslation("atelier")
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<string>("")
  const [ci, setCI] = useState<AtelierCI>(DEFAULT_CI)
  const [characters, setCharacters] = useState<AtelierCharacter[]>([])
  const [gallery, setGallery] = useState<GalleryItem[]>([])
  const [audioLibrary, setAudioLibrary] = useState<AudioLibraryItem[]>([])
  const [root, setRoot] = useState<string>("")
  const [presets, setPresets] = useState<PresetCatalog>({})
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [videoTick, setVideoTick] = useState(0)
  const [tab, setTab] = useState<AtelierTab>("generate")
  const [repeat, setRepeat] = useState<RepeatInput | null>(null)

  /** "Wiederholen" aus der Galerie: Charaktere + Parameter des Bildes
   *  übernehmen und in den Generieren-Tab wechseln. */
  const handleRepeat = useCallback((item: GalleryItem) => {
    setSelectedIds(item.character_ids ?? [])
    setRepeat({
      scene: item.scene ?? "",
      character_ids: item.character_ids ?? [],
      model: item.model ?? "",
      seed: item.seed ?? null,
      aspect_ratio: item.aspect_ratio ?? "",
      camera: item.camera ?? {},
      style: item.style ?? "",
    })
    setTab("generate")
  }, [])

  useEffect(() => {
    projectsApi.list().then((ps) => {
      setProjects(ps)
      if (ps.length > 0) setProjectId((cur) => cur || ps[0].id)
    })
    atelierApi.presets().then(setPresets).catch(() => setPresets({}))
  }, [])

  const reload = useCallback(async (pid: string) => {
    if (!pid) return
    const [meta, c, chars, gal, audioLib] = await Promise.all([
      atelierApi.meta(pid),
      atelierApi.getCI(pid),
      atelierApi.listCharacters(pid),
      atelierApi.gallery(pid),
      atelierApi.audioLibrary(pid),
    ])
    setRoot(meta.root)
    setCI(c)
    setCharacters(chars)
    setGallery(gal)
    setAudioLibrary(audioLib)
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

  const activeTab = TABS.find((it) => it.key === tab) ?? TABS[1]

  if (projects.length === 0) {
    return <div className="p-6 text-slate-400">{t("no_projects")}</div>
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-slate-950/40">
      <header className="flex items-center gap-3 border-b border-slate-700 bg-slate-900/60 px-4 py-3">
        <h1 className="text-lg font-semibold text-slate-100">🎨 {t("title")}</h1>
        <HelpButton topic="atelier" />
        <div className="ml-auto flex items-center gap-2">
          <label className="text-xs text-slate-400">{t("project")}</label>
          <select
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value)
              setSelectedIds([])
            }}
            className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm text-slate-100"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col gap-3 p-4">
        <nav className="flex flex-wrap gap-1 rounded-xl border border-slate-800 bg-slate-900/70 p-1">
          {TABS.map((item) => (
            <button
              key={item.key}
              onClick={() => setTab(item.key)}
              className={`min-w-[7.5rem] flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                tab === item.key
                  ? "bg-emerald-600 text-white shadow shadow-emerald-950/40"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              <span className="mr-1.5">{item.icon}</span>
              {t(item.labelKey)}
            </button>
          ))}
        </nav>

        <TabHelp title={`${activeTab.icon} ${t(activeTab.labelKey)}`} text={t(activeTab.helpKey)} />

        <section className="min-h-0 flex-1 overflow-auto rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          {tab === "characters" && (
            <CharacterLibrary
              projectId={projectId}
              characters={characters}
              selectedIds={selectedIds}
              onToggle={toggle}
              onChanged={() => reload(projectId)}
              refAbsPath={refAbsPath}
            />
          )}
          {tab === "generate" && (
            <GeneratePanel
              projectId={projectId}
              ci={ci}
              characters={characters}
              selectedIds={selectedIds}
              presets={presets}
              repeat={repeat}
              onGenerated={() => { reload(projectId); setTab("gallery") }}
            />
          )}
          {tab === "gallery" && (
            <ImageGalleryPanel
              projectId={projectId}
              items={gallery}
              characters={characters}
              onPromoted={() => reload(projectId)}
              onVideoStarted={() => { setVideoTick((n) => n + 1); setTab("clips") }}
              onRepeat={handleRepeat}
            />
          )}
          {tab === "clips" && (
            <ClipLibraryPanel key={`${projectId}-${videoTick}`} projectId={projectId} refAbsPath={refAbsPath} />
          )}
          {tab === "audio" && (
            <AudioPanel projectId={projectId} refAbsPath={refAbsPath} />
          )}
          {tab === "films" && (
            <FilmComposerPanel
              key={`film-${projectId}-${videoTick}`}
              projectId={projectId}
              refAbsPath={refAbsPath}
              audioLibrary={audioLibrary}
            />
          )}
          {tab === "cut" && <AtelierCutPanel projectId={projectId} />}
          {tab === "regie" && (
            <DirectorPanel projectId={projectId} characters={characters} presets={presets} />
          )}
        </section>
      </main>
    </div>
  )
}

function TabHelp({ title, text }: { title: string; text: string }) {
  const [open, setOpen] = useState(true)
  return (
    <aside className="rounded-xl border border-sky-500/20 bg-sky-500/10 p-3 text-sm text-sky-100">
      <button
        type="button"
        onClick={() => setOpen((cur) => !cur)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <span className="font-semibold">{title}</span>
        <span className="text-xs text-sky-300">{open ? "–" : "+"}</span>
      </button>
      {open && <p className="mt-1 max-w-5xl text-xs leading-relaxed text-sky-100/80">{text}</p>}
    </aside>
  )
}
