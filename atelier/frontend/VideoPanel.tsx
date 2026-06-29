import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import { VideoDialog } from "./VideoDialog"
import type { VideoJob } from "./types"

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
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const list = await atelierApi.listVideos(projectId)
        if (!alive) return
        setJobs(list)
        if (list.some((j) => ACTIVE.has(j.status))) {
          timer.current = setTimeout(load, 5000)
        }
      } catch {
        /* still: nächster Versuch beim nächsten reload */
      }
    }
    load()
    return () => {
      alive = false
      if (timer.current) clearTimeout(timer.current)
    }
  }, [projectId])

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
        <div key={job.job_id} className="rounded border border-slate-700 overflow-hidden">
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
          {job.prompt && (
            <p className="px-2 py-1 text-[10px] text-slate-500 truncate">{job.prompt}</p>
          )}
        </div>
      ))}
    </div>
  )
}
