import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import type { GalleryItem, MediaModel } from "./types"

export interface VideoInitial {
  prompt?: string
  model?: string
  duration?: number
  aspect_ratio?: string
  source_rel?: string  // Startbild/Referenz des Original-Jobs — beim Wiederholen mitführen
}

interface Props {
  projectId: string
  source: GalleryItem | null  // null = Text-to-Video (kein Startbild)
  onClose: () => void
  onStarted: () => void
  initial?: VideoInitial  // Vorbefüllung (Wiederholen eines Jobs / letzter Prompt)
}

// Fallback-Werte, wenn ein Modell keine Metadaten liefert.
const FALLBACK_DURATIONS = [5, 10]
const FALLBACK_ASPECTS = ["16:9", "9:16", "1:1"]

const durationsOf = (m?: MediaModel) =>
  (m?.durations && m.durations.length ? m.durations : FALLBACK_DURATIONS)
const aspectsOf = (m?: MediaModel) =>
  (m?.aspect_ratios && m.aspect_ratios.length ? m.aspect_ratios : FALLBACK_ASPECTS)

/** Dialog: aus einem Galerie-Bild ein Video machen (Image-to-Video). */
export function VideoGenerationDialog({ projectId, source, onClose, onStarted, initial }: Props) {
  const { t } = useTranslation("atelier")
  const [models, setModels] = useState<MediaModel[]>([])
  const [prompt, setPrompt] = useState(initial?.prompt ?? "")
  const [model, setModel] = useState(initial?.model ?? "")
  const [duration, setDuration] = useState(initial?.duration ?? FALLBACK_DURATIONS[0])
  const [aspect, setAspect] = useState(initial?.aspect_ratio ?? FALLBACK_ASPECTS[0])
  const [gallery, setGallery] = useState<GalleryItem[]>([])
  const [endRel, setEndRel] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    atelierApi.mediaModels("video").then((r) => {
      setModels(r.models)
      // Vorbefülltes Modell (Wiederholen) hat Vorrang, sonst Default/erstes.
      const chosen = initial?.model || r.default || r.models[0]?.id || ""
      if (chosen) {
        setModel(chosen)
        const meta = r.models.find((m) => m.id === chosen)
        const allowedD = durationsOf(meta)
        const allowedA = aspectsOf(meta)
        // Vorbefüllte Dauer/Aspect nur übernehmen, wenn fürs Modell gültig.
        setDuration(initial?.duration && allowedD.includes(initial.duration) ? initial.duration : allowedD[0])
        setAspect(initial?.aspect_ratio && allowedA.includes(initial.aspect_ratio) ? initial.aspect_ratio : allowedA[0])
      }
    }).catch(() => setModels([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Galerie nur laden, wenn ein Startbild existiert (Endbild braucht ein Startbild).
  const effectiveSourceRel = source?.rel || initial?.source_rel || ""
  useEffect(() => {
    if (!effectiveSourceRel) return
    atelierApi.gallery(projectId)
      .then((items) => setGallery(items.filter((it) => it.rel !== effectiveSourceRel)))
      .catch(() => setGallery([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, effectiveSourceRel])

  const current = models.find((m) => m.id === model)
  const durations = durationsOf(current)
  const aspects = aspectsOf(current)
  const supportsLastFrame = (current?.frame_images ?? []).includes("last_frame")
  const showEndField = Boolean(effectiveSourceRel) && supportsLastFrame

  function pickModel(m: string) {
    setModel(m)
    const meta = models.find((x) => x.id === m)
    const allowedD = durationsOf(meta)
    if (!allowedD.includes(duration)) setDuration(allowedD[0])
    const allowedA = aspectsOf(meta)
    if (!allowedA.includes(aspect)) setAspect(allowedA[0])
  }

  async function start() {
    setBusy(true)
    setError(null)
    try {
      await atelierApi.createVideo(projectId, {
        source_rel: effectiveSourceRel,
        end_source_rel: showEndField ? endRel : "",
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
        {!source && effectiveSourceRel && (
          <div className="text-[10px] text-emerald-300 bg-emerald-500/10 rounded px-2 py-1">
            🖼️ {t("repeat_uses_reference")}
          </div>
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
              {models.length === 0 && <option value="">…</option>}
              {models.map((m) => (
                <option key={m.id} value={m.id}>{m.name || m.id.split("/")[1] || m.id}</option>
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

        {showEndField && (
          <div className="flex flex-col gap-1 text-xs text-slate-400">
            {t("video_end_image")}
            <div className="grid grid-cols-4 gap-1.5 max-h-40 overflow-y-auto rounded bg-slate-800/60 border border-slate-700 p-1.5">
              <button
                type="button"
                onClick={() => setEndRel("")}
                className={`aspect-square rounded grid place-items-center text-[9px] leading-tight text-center px-0.5 border ${
                  endRel === "" ? "border-emerald-500 bg-emerald-500/15 text-emerald-200" : "border-slate-600 bg-slate-900/60 text-slate-400 hover:border-slate-500"
                }`}
                title={t("video_end_image_none")}
              >
                {t("video_end_image_none")}
              </button>
              <button
                type="button"
                onClick={() => setEndRel(effectiveSourceRel)}
                className={`aspect-square rounded grid place-items-center text-[9px] leading-tight text-center px-0.5 border ${
                  endRel === effectiveSourceRel ? "border-emerald-500 bg-emerald-500/15 text-emerald-200" : "border-slate-600 bg-slate-900/60 text-slate-300 hover:border-slate-500"
                }`}
                title={t("video_end_image_loop")}
              >
                <span><span className="block text-base">🔁</span>{t("video_end_image_loop")}</span>
              </button>
              {gallery.map((it) => (
                <button
                  type="button"
                  key={it.rel}
                  onClick={() => setEndRel(it.rel)}
                  title={it.prompt || it.name}
                  className={`relative aspect-square overflow-hidden rounded border ${
                    endRel === it.rel ? "border-emerald-500 ring-1 ring-emerald-500" : "border-slate-600 hover:border-slate-400"
                  }`}
                >
                  <img src={fileUrl(it.path)} alt="" loading="lazy" className="h-full w-full object-cover" />
                  {endRel === it.rel && (
                    <span className="absolute right-0.5 top-0.5 rounded-full bg-emerald-500 px-1 text-[8px] text-white">✓</span>
                  )}
                </button>
              ))}
            </div>
            <span className="text-[10px] text-slate-500">{t("video_end_image_hint")}</span>
          </div>
        )}

        <p className="text-[10px] text-amber-400">{t("video_cost_hint")}</p>
        {error && <div className="text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">{error}</div>}

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="text-xs px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600">
            {t("cancel")}
          </button>
          <button
            onClick={start}
            disabled={busy || (!effectiveSourceRel && !prompt.trim())}
            className="text-xs px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 font-medium"
          >
            {busy ? t("video_starting") : t("video_start")}
          </button>
        </div>
      </div>
    </div>
  )
}
