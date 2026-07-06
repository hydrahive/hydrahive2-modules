import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi } from "./api"
import type { AtelierCharacter, Shot } from "./types"

interface Props {
  projectId: string
  sceneId: string
  characters: AtelierCharacter[]
  /** Trigger zum Neuladen (z.B. nach Zerlegen hochzählen). */
  reloadKey: number
}

function statusClass(status: string): string {
  if (status === "done") return "bg-emerald-500/20 text-emerald-300"
  if (status === "failed") return "bg-rose-500/20 text-rose-300"
  if (status === "video_processing" || status === "image_ready") return "bg-amber-500/20 text-amber-300"
  return "bg-slate-600/30 text-slate-300"
}

/** Storyboard-Vorschau: die vom Regieagenten erzeugten Shots einer Szene.
 *  Editierbar (Prompt/Dauer) + löschbar. Reiner Planungs-Zustand (status
 *  "planned") — Batch-Render folgt in E5. */
export function ShotStoryboard({ projectId, sceneId, characters, reloadKey }: Props) {
  const { t } = useTranslation("atelier")
  const [shots, setShots] = useState<Shot[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    atelierApi.listShots(projectId, sceneId)
      .then(setShots)
      .catch(() => setShots([]))
      .finally(() => setLoading(false))
  }, [projectId, sceneId, reloadKey])

  async function patch(shotId: string, body: Partial<Shot>) {
    const upd = await atelierApi.updateShot(projectId, sceneId, shotId, body)
    setShots((cur) => cur.map((s) => (s.id === shotId ? upd : s)))
  }
  async function remove(shotId: string) {
    await atelierApi.deleteShot(projectId, sceneId, shotId)
    setShots((cur) => cur.filter((s) => s.id !== shotId))
  }

  const charName = (id: string) => characters.find((c) => c.id === id)?.name || id.slice(0, 6)

  if (loading) return <p className="text-[10px] text-slate-500 px-2">{t("saving")}</p>
  if (shots.length === 0) return null

  return (
    <div className="flex flex-col gap-1.5 mt-1">
      <span className="text-[10px] font-semibold text-violet-300 px-1">
        🎞️ {t("shots_word")} ({shots.length})
      </span>
      {shots.map((sh, i) => (
        <div key={sh.id} className="rounded border border-violet-500/20 bg-violet-500/5 p-2 flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-violet-300 font-mono">#{i + 1}</span>
            {sh.shot && <span className="text-[9px] px-1 rounded bg-violet-500/20 text-violet-200">{sh.shot}</span>}
            <span className="text-[9px] text-slate-500">{sh.duration}s</span>
            {sh.status && sh.status !== "planned" && (
              <span className={`text-[9px] px-1 rounded ${statusClass(sh.status)}`}>
                {t(`shot_status_${sh.status}`, sh.status)}
              </span>
            )}
            <div className="flex-1" />
            <button onClick={() => remove(sh.id)} className="text-slate-500 hover:text-rose-400 text-xs">✕</button>
          </div>
          <textarea
            value={sh.prompt}
            onChange={(e) => setShots((cur) => cur.map((s) => (s.id === sh.id ? { ...s, prompt: e.target.value } : s)))}
            onBlur={(e) => patch(sh.id, { prompt: e.target.value })}
            rows={2}
            className="text-[10px] px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-200 resize-y"
          />
          {sh.character_ids.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {sh.character_ids.map((id) => (
                <span key={id} className="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-600/20 text-emerald-200">
                  {charName(id)}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
