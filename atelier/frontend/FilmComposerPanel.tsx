import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import type { AudioLibraryItem, FilmJob, VideoJob } from "./types"

interface Props {
  projectId: string
  refAbsPath: (rel: string) => string
  audioLibrary: AudioLibraryItem[]
}

const ACTIVE = new Set(["pending", "processing"])

/** Film-Schnitt: fertige Clips in Reihenfolge wählen → rendern → Player.
 *  Pollt alle 5s, solange ein Render-Job läuft. */
export function FilmComposerPanel({ projectId, refAbsPath, audioLibrary }: Props) {
  const { t } = useTranslation("atelier")
  const [videos, setVideos] = useState<VideoJob[]>([])
  const [order, setOrder] = useState<string[]>([])
  const [resolution, setResolution] = useState("16:9")
  const [musicRel, setMusicRel] = useState("")
  const [jobs, setJobs] = useState<FilmJob[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    atelierApi.listVideos(projectId).then(setVideos).catch(() => setVideos([]))
  }, [projectId, busy])

  const clips = videos.filter((v) => v.status === "completed" && v.video_rel)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const list = await atelierApi.listFilms(projectId)
        if (!alive) return
        setJobs(list)
        if (list.some((j) => ACTIVE.has(j.status))) timer.current = setTimeout(load, 5000)
      } catch { /* retry beim nächsten Trigger */ }
    }
    load()
    return () => { alive = false; if (timer.current) clearTimeout(timer.current) }
  }, [projectId, busy])

  function toggle(rel: string) {
    setOrder((cur) => (cur.includes(rel) ? cur.filter((r) => r !== rel) : [...cur, rel]))
  }

  async function del(job: FilmJob) {
    if (!confirm(t("delete_film_confirm"))) return
    await atelierApi.deleteFilm(projectId, job.job_id)
    setJobs((cur) => cur.filter((j) => j.job_id !== job.job_id))
  }

  async function render() {
    if (order.length < 1) return
    setBusy(true); setError(null)
    try {
      await atelierApi.createFilm(projectId, order, resolution, musicRel)
      setOrder([])
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-slate-200">🎞️ {t("film_title")}</h3>

      {clips.length === 0 && jobs.length === 0 && (
        <p className="text-xs text-slate-500">{t("film_empty")}</p>
      )}

      {clips.length > 0 && (
        <>
          <p className="text-[10px] text-slate-500">{t("film_hint")}</p>
          <div className="flex flex-col gap-1">
            {clips.map((v) => {
              const rel = v.video_rel as string
              const pos = order.indexOf(rel)
              return (
                <button
                  key={v.job_id}
                  onClick={() => toggle(rel)}
                  className={`flex items-center gap-2 rounded border px-2 py-1 text-left text-xs transition-colors ${
                    pos >= 0 ? "border-emerald-500 bg-emerald-500/10" : "border-slate-700 bg-slate-800/50"
                  }`}
                >
                  <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full text-[10px] ${pos >= 0 ? "bg-emerald-600 text-white" : "bg-slate-700 text-slate-400"}`}>
                    {pos >= 0 ? pos + 1 : "+"}
                  </span>
                  <span className="truncate text-slate-300">{v.prompt || t("untitled")}</span>
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-2">
            <select
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-xs text-slate-100"
            >
              <option value="16:9">16:9</option>
              <option value="9:16">9:16</option>
              <option value="1:1">1:1</option>
            </select>
            <select
              value={musicRel}
              onChange={(e) => setMusicRel(e.target.value)}
              title={t("film_music")}
              className="min-w-0 flex-1 rounded bg-slate-800 border border-slate-700 px-2 py-1 text-xs text-slate-100 truncate"
            >
              <option value="">{t("film_music_none")}</option>
              {audioLibrary.map((a) => (
                <option key={a.rel} value={a.rel}>{a.prompt || a.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={render}
            disabled={busy || order.length < 1}
            className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-medium hover:bg-emerald-500 disabled:opacity-40"
          >
            {busy ? t("film_rendering") : t("film_render", { n: order.length })}
          </button>
        </>
      )}

      {error && <div className="rounded bg-red-500/10 px-2 py-1 text-xs text-red-400">{error}</div>}

      {jobs.map((job) => (
        <div key={job.job_id} className="group relative overflow-hidden rounded border border-slate-700">
          {job.status === "completed" && job.film_rel ? (
            <video src={fileUrl(refAbsPath(job.film_rel))} controls className="w-full" preload="metadata" />
          ) : (
            <div className="flex items-center gap-2 p-2 text-xs">
              {ACTIVE.has(job.status) ? (
                <>
                  <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                  <span className="text-slate-300">{t("film_processing")}</span>
                </>
              ) : (
                <span className="text-red-400">⚠ {job.error || t("film_failed")}</span>
              )}
            </div>
          )}
          <button
            onClick={() => del(job)}
            title={t("delete")}
            className="absolute top-1 right-1 rounded bg-black/60 px-1.5 py-0.5 text-[11px] opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
          >
            🗑️
          </button>
        </div>
      ))}
    </div>
  )
}
