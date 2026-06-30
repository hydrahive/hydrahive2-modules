import { useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import type { GalleryItem } from "./types"

interface Props {
  projectId: string
  source: GalleryItem | null  // null = Text-to-Video (kein Startbild)
  onClose: () => void
  onStarted: () => void
}

// Erlaubte Dauern je Modell (aus OpenRouter — Modelle akzeptieren nur bestimmte
// Werte, sonst HTTP 400). Erster Wert = Default.
const MODEL_DURATIONS: Record<string, number[]> = {
  "minimax/hailuo-2.3": [6, 10],
  "kwaivgi/kling-v3.0-std": [5, 10],
  "bytedance/seedance-2.0-fast": [5, 10],
}
// Erlaubte Formate je Modell (supported_aspect_ratios der OpenRouter-API).
// Erster Wert = Default. hailuo kann nur 16:9, seedance fast alles.
const MODEL_ASPECTS: Record<string, string[]> = {
  "minimax/hailuo-2.3": ["16:9"],
  "kwaivgi/kling-v3.0-std": ["16:9", "9:16", "1:1"],
  "bytedance/seedance-2.0-fast": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "9:21"],
}
const MODELS = Object.keys(MODEL_DURATIONS)

/** Dialog: aus einem Galerie-Bild ein Video machen (Image-to-Video). */
export function VideoDialog({ projectId, source, onClose, onStarted }: Props) {
  const { t } = useTranslation("atelier")
  const [prompt, setPrompt] = useState("")
  const [model, setModel] = useState(MODELS[0])
  const [duration, setDuration] = useState(MODEL_DURATIONS[MODELS[0]][0])
  const [aspect, setAspect] = useState(MODEL_ASPECTS[MODELS[0]][0])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const durations = MODEL_DURATIONS[model] ?? [5]
  const aspects = MODEL_ASPECTS[model] ?? ["16:9"]

  function pickModel(m: string) {
    setModel(m)
    // Dauer + Format auf für das neue Modell gültige Werte setzen.
    const allowedD = MODEL_DURATIONS[m] ?? [5]
    if (!allowedD.includes(duration)) setDuration(allowedD[0])
    const allowedA = MODEL_ASPECTS[m] ?? ["16:9"]
    if (!allowedA.includes(aspect)) setAspect(allowedA[0])
  }

  async function start() {
    setBusy(true)
    setError(null)
    try {
      await atelierApi.createVideo(projectId, {
        source_rel: source?.rel ?? "",
        prompt,
        model,
        duration,
        aspect_ratio: aspect,
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
        <h4 className="text-sm font-semibold text-slate-200">
          🎬 {source ? t("make_video") : t("make_video_text")}
        </h4>
        {source && (
          <img src={fileUrl(source.path)} alt="" className="w-full rounded max-h-40 object-contain bg-black/30" />
        )}

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
              onChange={(e) => pickModel(e.target.value)}
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
              {durations.map((d) => (
                <option key={d} value={d}>{d}s</option>
              ))}
            </select>
          </label>
        </div>

        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t("video_aspect")}
          <select
            value={aspect}
            onChange={(e) => setAspect(e.target.value)}
            className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
          >
            {aspects.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </label>
        {source && <p className="text-[10px] text-slate-500">{t("video_aspect_hint")}</p>}

        <p className="text-[10px] text-amber-400">{t("video_cost_hint")}</p>
        {error && <div className="text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">{error}</div>}

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="text-xs px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600">
            {t("cancel")}
          </button>
          <button
            onClick={start}
            disabled={busy || (!source && !prompt.trim())}
            className="text-xs px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 font-medium"
          >
            {busy ? t("video_starting") : t("video_start")}
          </button>
        </div>
      </div>
    </div>
  )
}
