import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi } from "./api"
import { AudioProfiles } from "./AudioProfiles"
import { AudioLibrary } from "./AudioLibrary"
import type { AudioLibraryItem, AudioProfile } from "./types"

interface Props {
  projectId: string
  refAbsPath: (rel: string) => string
}

/** Audio-Tab: Studio-Sound-Anker + Sound-Profile + Musik generieren + Bibliothek.
 *  Eigener Reload-Kreislauf (unabhängig von Bild/Video/Film), da Musik keinen
 *  Job-Poll braucht — Lyria antwortet synchron in ~10-30s. */
export function AudioPanel({ projectId, refAbsPath }: Props) {
  const { t } = useTranslation("atelier")
  const [anchor, setAnchor] = useState("")
  const [profiles, setProfiles] = useState<AudioProfile[]>([])
  const [library, setLibrary] = useState<AudioLibraryItem[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [scene, setScene] = useState("")
  const [busy, setBusy] = useState(false)
  const [savingAnchor, setSavingAnchor] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    if (!projectId) return
    const [a, p, lib] = await Promise.all([
      atelierApi.getMusicAnchor(projectId),
      atelierApi.listAudioProfiles(projectId),
      atelierApi.audioLibrary(projectId),
    ])
    setAnchor(a.music_style_anchor)
    setProfiles(p)
    setLibrary(lib)
  }

  useEffect(() => { reload() }, [projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  function toggle(id: string) {
    setSelectedIds((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))
  }

  async function saveAnchor() {
    setSavingAnchor(true)
    try {
      await atelierApi.saveMusicAnchor(projectId, anchor)
    } finally {
      setSavingAnchor(false)
    }
  }

  async function generate() {
    setBusy(true); setError(null)
    try {
      await atelierApi.generateMusic(projectId, { scene, profile_ids: selectedIds })
      setScene("")
      await reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid grid-cols-[280px_1fr] gap-4 h-full">
      <section className="overflow-auto">
        <AudioProfiles
          projectId={projectId}
          profiles={profiles}
          selectedIds={selectedIds}
          onToggle={toggle}
          onChanged={reload}
        />
      </section>

      <section className="flex flex-col gap-3 overflow-auto">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-300">🎚️ {t("audio_studio_sound")}</label>
          <textarea
            value={anchor}
            onChange={(e) => setAnchor(e.target.value)}
            onBlur={saveAnchor}
            placeholder={t("audio_studio_sound_placeholder")}
            rows={2}
            className="text-xs px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-slate-100 resize-y"
          />
          {savingAnchor && <span className="text-[10px] text-slate-500">{t("saving")}</span>}
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-300">✨ {t("audio_scene")}</label>
          <textarea
            value={scene}
            onChange={(e) => setScene(e.target.value)}
            placeholder={t("audio_scene_placeholder")}
            rows={3}
            className="text-xs px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-slate-100 resize-y"
          />
        </div>

        <button
          onClick={generate}
          disabled={busy}
          className="rounded bg-emerald-600 px-3 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-40"
        >
          {busy ? t("audio_generating") : t("audio_generate")}
        </button>

        {error && <div className="rounded bg-red-500/10 px-2 py-1 text-xs text-red-400">{error}</div>}

        <AudioLibrary projectId={projectId} items={library} refAbsPath={refAbsPath} onChanged={reload} />
      </section>
    </div>
  )
}
