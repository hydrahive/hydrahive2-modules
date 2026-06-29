import { useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import type { GalleryItem } from "./types"

interface Props {
  projectId: string
  source: GalleryItem
  onClose: () => void
  onStarted: () => void
}

const MODELS = ["minimax/hailuo-2.3", "kwaivgi/kling-v3.0-std", "bytedance/seedance-2.0-fast"]
const DURATIONS = [5, 10]

/** Dialog: aus einem Galerie-Bild ein Video machen (Image-to-Video). */
export function VideoDialog({ projectId, source, onClose, onStarted }: Props) {
  const { t } = useTranslation("atelier")
  const [prompt, setPrompt] = useState("")
  const [model, setModel] = useState(MODELS[0])
  const [duration, setDuration] = useState(5)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function start() {
    setBusy(true)
    setError(null)
    try {
      await atelierApi.createVideo(projectId, {
        source_rel: source.rel,
        prompt,
        model,
        duration,
      })
      onStarted()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 grid place-items-center p-6" onClick={onClose}>
      <div
        className="bg-slate-900 border border-slate-700 rounded-lg p-4 flex flex-col gap-3 max-w-sm w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <h4 className="text-sm font-semibold text-slate-200">🎬 {t("make_video")}</h4>
        <img src={fileUrl(source.path)} alt="" className="w-full rounded max-h-40 object-contain bg-black/30" />

        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t("video_motion")}
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={t("video_motion_hint")}
            rows={2}
            className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 resize-y"
          />
        </label>

        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            {t("model")}
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
            >
              {MODELS.map((m) => (
                <option key={m} value={m}>{m.split("/")[1]}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            {t("video_duration")}
            <select
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
            >
              {DURATIONS.map((d) => (
                <option key={d} value={d}>{d}s</option>
              ))}
            </select>
          </label>
        </div>

        <p className="text-[10px] text-amber-400">{t("video_cost_hint")}</p>
        {error && <div className="text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">{error}</div>}

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="text-xs px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600">
            {t("cancel")}
          </button>
          <button
            onClick={start}
            disabled={busy}
            className="text-xs px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 font-medium"
          >
            {busy ? t("video_starting") : t("video_start")}
          </button>
        </div>
      </div>
    </div>
  )
}
