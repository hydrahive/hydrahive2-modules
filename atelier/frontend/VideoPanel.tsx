import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import { VideoDialog, type VideoInitial } from "./VideoDialog"
import { PromptView } from "./PromptView"
import type { GalleryItem, VideoJob } from "./types"

interface Props {
  projectId: string
  refAbsPath: (rel: string) => string
}

const ACTIVE = new Set(["pending", "processing"])

/** Video-Jobs des Projekts: laufende mit Status, fertige als Player.
 *  Plus "Video aus Text"-Einstieg (ohne Startbild). Pollt alle 5s, solange ein
 *  Job läuft. */
export function VideoPanel({ projectId, refAbsPath }: Props) {
  const { t } = useTranslation("atelier")
  const [jobs, setJobs] = useState<VideoJob[]>([])
  const [textDialog, setTextDialog] = useState(false)
  const [repeat, setRepeat] = useState<VideoInitial | null>(null)
  const [continueSource, setContinueSource] = useState<GalleryItem | null>(null)
  const [continuing, setContinuing] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  async function load() {
    try {
      const list = await atelierApi.listVideos(projectId)
      setJobs(list)
      if (list.some((j) => ACTIVE.has(j.status))) timer.current = setTimeout(load, 5000)
    } catch { /* retry beim nächsten Trigger */ }
  }

  useEffect(() => {
    load()
    return () => { if (timer.current) clearTimeout(timer.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  async function del(job: VideoJob) {
    if (!confirm(t("delete_video_confirm"))) return
    await atelierApi.deleteVideo(projectId, job.job_id)
    setJobs((cur) => cur.filter((j) => j.job_id !== job.job_id))
  }

  async function startContinue(job: VideoJob) {
    if (!job.video_rel) return
    setContinuing(job.job_id)
    try {
      const res = await atelierApi.continueFrame(projectId, job.video_rel)
      // Minimal-GalleryItem aus der Antwort (VideoDialog nutzt nur rel + path).
      setContinueSource({
        name: "", path: res.path, rel: res.rel,
        created_at: null, prompt: null, seed: null, model: null, mtime: 0,
      })
    } finally {
      setContinuing(null)
    }
  }

  return (
    <div className="flex flex-col gap-2 border-t border-slate-700 pt-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">🎬 {t("videos")}</h3>
        <button
          onClick={() => setTextDialog(true)}
          className="rounded-md border border-sky-500/30 bg-sky-500/10 px-2 py-1 text-xs text-sky-300 hover:bg-sky-500/20"
        >
          + {t("make_video_text")}
        </button>
      </div>

      {textDialog && (
        <VideoDialog
          projectId={projectId}
          source={null}
          onClose={() => setTextDialog(false)}
          onStarted={() => {
            setTextDialog(false)
            atelierApi.listVideos(projectId).then(setJobs).catch(() => {})
          }}
        />
      )}
      {jobs.map((job) => (
        <div key={job.job_id} className="group relative rounded border border-slate-700 overflow-hidden">
          {job.status === "completed" && job.video_rel ? (
            <video
              src={fileUrl(refAbsPath(job.video_rel))}
              controls
              className="w-full"
              preload="metadata"
            />
          ) : (
            <div className="p-3 flex items-center gap-2 text-xs">
              {ACTIVE.has(job.status) ? (
                <>
                  <span className="inline-block h-3 w-3 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin" />
                  <span className="text-slate-300">{t("video_generating")}</span>
                </>
              ) : (
                <span className="text-red-400">⚠ {job.error || t("video_failed")}</span>
              )}
            </div>
          )}
          {job.prompt && <PromptView text={job.prompt} />}
          <div className="flex flex-wrap items-center gap-1 px-2 pb-1 text-[9px] text-slate-500">
            {job.model && (
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300" title={t("video_meta_model")}>
                🤖 {job.model}
              </span>
            )}
            {job.duration != null && (
              <span className="px-1.5 py-0.5 rounded bg-slate-800" title={t("video_meta_duration")}>
                ⏱ {job.duration}s
              </span>
            )}
            {job.aspect_ratio && (
              <span className="px-1.5 py-0.5 rounded bg-slate-800" title={t("video_meta_aspect")}>
                🖼 {job.aspect_ratio}
              </span>
            )}
            <span className="px-1.5 py-0.5 rounded bg-slate-800" title={t("video_meta_source")}>
              {job.source_rel ? `🎞 ${t("video_meta_i2v")}` : `📝 ${t("video_meta_t2v")}`}
            </span>
          </div>
          <div className="flex flex-wrap gap-1 px-1 pb-1">
            <button
              onClick={() => setRepeat({
                prompt: job.prompt, model: job.model,
                duration: job.duration, aspect_ratio: job.aspect_ratio,
                source_rel: job.source_rel,
              })}
              className="rounded bg-slate-700/80 px-2 py-1 text-[10px] hover:bg-slate-600"
              title={t("repeat_hint")}
            >
              🔁 {t("repeat_video")}
            </button>
            {job.status === "completed" && job.video_rel && (
              <button
                onClick={() => startContinue(job)}
                disabled={continuing === job.job_id}
                className="rounded bg-violet-600/80 px-2 py-1 text-[10px] hover:bg-violet-500 disabled:opacity-40"
                title={t("continue_hint")}
              >
                {continuing === job.job_id ? t("continue_extracting") : `⏩ ${t("continue_video")}`}
              </button>
            )}
          </div>
          <button
            onClick={() => del(job)}
            title={t("delete")}
            className="absolute top-1 right-1 rounded bg-black/60 px-1.5 py-0.5 text-[11px] opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
          >
            🗑️
          </button>
        </div>
      ))}

      {continueSource && (
        <VideoDialog
          projectId={projectId}
          source={continueSource}
          onClose={() => setContinueSource(null)}
          onStarted={() => {
            setContinueSource(null)
            atelierApi.listVideos(projectId).then(setJobs).catch(() => {})
          }}
        />
      )}

      {repeat && (
        <VideoDialog
          projectId={projectId}
          source={null}
          initial={repeat}
          onClose={() => setRepeat(null)}
          onStarted={() => {
            setRepeat(null)
            atelierApi.listVideos(projectId).then(setJobs).catch(() => {})
          }}
        />
      )}
    </div>
  )
}
