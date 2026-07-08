import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import { VideoGenerationDialog, type VideoInitial } from "./VideoGenerationDialog"
import { PromptView } from "./PromptView"
import type { GalleryItem, VideoJob } from "./types"

interface Props {
  projectId: string
  refAbsPath: (rel: string) => string
}

const ACTIVE = new Set(["pending", "processing"])

/** Video-Jobs des Projekts: kompakte Thumbnail-Übersicht + Overlay-Player. */
export function ClipLibraryPanel({ projectId, refAbsPath }: Props) {
  const { t } = useTranslation("atelier")
  const [jobs, setJobs] = useState<VideoJob[]>([])
  const [textDialog, setTextDialog] = useState(false)
  const [repeat, setRepeat] = useState<VideoInitial | null>(null)
  const [continueSource, setContinueSource] = useState<GalleryItem | null>(null)
  const [continuing, setContinuing] = useState<string | null>(null)
  const [openJob, setOpenJob] = useState<VideoJob | null>(null)
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
    if (openJob?.job_id === job.job_id) setOpenJob(null)
  }

  async function startContinue(job: VideoJob) {
    if (!job.video_rel) return
    setContinuing(job.job_id)
    try {
      const res = await atelierApi.continueFrame(projectId, job.video_rel)
      // Minimal-GalleryItem aus der Antwort (VideoGenerationDialog nutzt nur rel + path).
      setContinueSource({
        name: "", path: res.path, rel: res.rel,
        created_at: null, prompt: null, seed: null, model: null, mtime: 0,
      })
    } finally {
      setContinuing(null)
    }
  }

  function initialFrom(job: VideoJob): VideoInitial {
    return {
      prompt: job.prompt, model: job.model,
      duration: job.duration, aspect_ratio: job.aspect_ratio,
      source_rel: job.source_rel,
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">🎬 {t("videos")}</h3>
          <p className="text-xs text-slate-500">{jobs.length} {t("video_items")}</p>
        </div>
        <button
          onClick={() => setTextDialog(true)}
          className="rounded-md border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs text-sky-300 hover:bg-sky-500/20"
        >
          + {t("make_video_text")}
        </button>
      </div>

      {textDialog && (
        <VideoGenerationDialog
          projectId={projectId}
          source={null}
          onClose={() => setTextDialog(false)}
          onStarted={() => {
            setTextDialog(false)
            atelierApi.listVideos(projectId).then(setJobs).catch(() => {})
          }}
        />
      )}

      {jobs.length === 0 && <p className="text-xs text-slate-500">{t("video_empty")}</p>}
      <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
        {jobs.map((job) => (
          <VideoCard
            key={job.job_id}
            job={job}
            refAbsPath={refAbsPath}
            onOpen={() => job.status === "completed" && job.video_rel ? setOpenJob(job) : undefined}
            onDelete={() => del(job)}
            onRepeat={() => setRepeat(initialFrom(job))}
            onContinue={() => startContinue(job)}
            continuing={continuing === job.job_id}
          />
        ))}
      </div>

      {continueSource && (
        <VideoGenerationDialog
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
        <VideoGenerationDialog
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

      {openJob && (
        <VideoOverlay
          job={openJob}
          src={fileUrl(refAbsPath(openJob.video_rel || ""))}
          onClose={() => setOpenJob(null)}
          onRepeat={() => setRepeat(initialFrom(openJob))}
          onContinue={() => startContinue(openJob)}
          onDelete={() => del(openJob)}
          continuing={continuing === openJob.job_id}
        />
      )}
    </div>
  )
}

function VideoCard({ job, refAbsPath, onOpen, onDelete, onRepeat, onContinue, continuing }: {
  job: VideoJob
  refAbsPath: (rel: string) => string
  onOpen: () => void
  onDelete: () => void
  onRepeat: () => void
  onContinue: () => void
  continuing: boolean
}) {
  const { t } = useTranslation("atelier")
  const videoRef = useRef<HTMLVideoElement>(null)
  const isDone = job.status === "completed" && Boolean(job.video_rel)
  const src = isDone ? fileUrl(refAbsPath(job.video_rel || "")) : ""

  return (
    <div className="group overflow-hidden rounded-lg border border-slate-700 bg-slate-900/50">
      <button
        type="button"
        onClick={onOpen}
        disabled={!isDone}
        className="relative block w-full bg-black/60 text-left disabled:cursor-default"
        onMouseEnter={() => videoRef.current?.play().catch(() => {})}
        onMouseLeave={() => { if (videoRef.current) { videoRef.current.pause(); videoRef.current.currentTime = 0 } }}
      >
        <div className="aspect-video grid place-items-center overflow-hidden">
          {isDone ? (
            <video ref={videoRef} src={src} muted loop preload="metadata" className="h-full w-full object-cover" />
          ) : ACTIVE.has(job.status) ? (
            <div className="flex flex-col items-center gap-2 text-xs text-slate-300">
              <span className="inline-block h-5 w-5 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin" />
              <span>{t("video_generating")}</span>
            </div>
          ) : (
            <span className="p-4 text-xs text-red-400">⚠ {job.error || t("video_failed")}</span>
          )}
        </div>
        {isDone && <span className="absolute left-2 top-2 rounded-full bg-black/70 px-2 py-1 text-xs">▶</span>}
      </button>

      <div className="space-y-2 p-2">
        {job.prompt && <PromptView text={job.prompt} clamp={2} />}
        <div className="flex flex-wrap items-center gap-1 text-[9px] text-slate-500">
          {job.model && <span className="rounded bg-slate-800 px-1.5 py-0.5 text-slate-300">🤖 {job.model}</span>}
          {job.duration != null && <span className="rounded bg-slate-800 px-1.5 py-0.5">⏱ {job.duration}s</span>}
          {job.aspect_ratio && <span className="rounded bg-slate-800 px-1.5 py-0.5">🖼 {job.aspect_ratio}</span>}
          <span className="rounded bg-slate-800 px-1.5 py-0.5">
            {job.source_rel ? `🎞 ${t("video_meta_i2v")}` : `📝 ${t("video_meta_t2v")}`}
          </span>
        </div>
        <div className="flex flex-wrap gap-1">
          <button onClick={onRepeat} className="rounded bg-slate-700/80 px-2 py-1 text-[10px] hover:bg-slate-600">🔁 {t("repeat_video")}</button>
          {isDone && (
            <button onClick={onContinue} disabled={continuing} className="rounded bg-violet-600/80 px-2 py-1 text-[10px] hover:bg-violet-500 disabled:opacity-40">
              {continuing ? t("continue_extracting") : `⏩ ${t("continue_video")}`}
            </button>
          )}
          <button onClick={onDelete} className="ml-auto rounded bg-red-600/80 px-2 py-1 text-[10px] hover:bg-red-500">🗑️</button>
        </div>
      </div>
    </div>
  )
}

function VideoOverlay({ job, src, onClose, onRepeat, onContinue, onDelete, continuing }: {
  job: VideoJob
  src: string
  onClose: () => void
  onRepeat: () => void
  onContinue: () => void
  onDelete: () => void
  continuing: boolean
}) {
  const { t } = useTranslation("atelier")
  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 bg-black/85 p-4" onClick={onClose}>
      <div className="mx-auto flex h-full max-w-6xl flex-col gap-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between text-xs text-slate-300">
          <span>{job.video_rel}</span>
          <button onClick={onClose} className="rounded bg-slate-800 px-3 py-1 hover:bg-slate-700">{t("close")}</button>
        </div>
        <video src={src} controls autoPlay className="min-h-0 flex-1 rounded-lg bg-black object-contain" />
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs text-slate-300">
          {job.prompt && <PromptView text={job.prompt} />}
          <div className="mt-2 flex flex-wrap gap-2 text-slate-400">
            {job.model && <span>🤖 {job.model}</span>}
            {job.duration != null && <span>⏱ {job.duration}s</span>}
            {job.aspect_ratio && <span>🖼 {job.aspect_ratio}</span>}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button onClick={onRepeat} className="rounded bg-slate-700 px-3 py-1 hover:bg-slate-600">🔁 {t("repeat_video")}</button>
            <button onClick={onContinue} disabled={continuing} className="rounded bg-violet-600 px-3 py-1 hover:bg-violet-500 disabled:opacity-40">
              {continuing ? t("continue_extracting") : `⏩ ${t("continue_video")}`}
            </button>
            <button className="rounded bg-sky-700/80 px-3 py-1 text-sky-100 opacity-60" title={t("cut_coming_title")}>✂️ {t("tab_cut")}</button>
            <button onClick={onDelete} className="ml-auto rounded bg-red-600/80 px-3 py-1 hover:bg-red-500">🗑️ {t("delete")}</button>
          </div>
        </div>
      </div>
    </div>
  )
}
