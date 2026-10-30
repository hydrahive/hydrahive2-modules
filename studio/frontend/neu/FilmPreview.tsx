/** G5: Vorschau des Films aus den Karten (vor dem Erzeugen) – Abspielen/Anhalten, Szenenleiste zum Springen. */
import { useEffect, useState } from "react"
import { Pause, Play } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { Plan } from "../planApi"
import { fileOf } from "../planLogic"
import { previewFrames } from "./guidedLogic"

export function FilmPreview({ plan }: { plan: Plan | null }) {
  const { t } = useTranslation("studio")
  const frames = previewFrames(plan)
  const [at, setAt] = useState(0)
  const [playing, setPlaying] = useState(false)
  const i = frames.length ? at % frames.length : 0
  const cur = frames[i]
  useEffect(() => {
    if (!playing || !cur) return
    const h = window.setTimeout(() => setAt((a) => a + 1), Math.max(1, cur.seconds) * 1000)
    return () => window.clearTimeout(h)
  }, [playing, cur, at])
  const base = plan?.base ?? ""
  const tall = plan?.screenplay.aspect_ratio === "9:16"
  return (
    <section>
      <div className={`relative mx-auto overflow-hidden rounded-[12px] bg-black ${tall ? "aspect-[9/16] max-h-[560px]" : "aspect-video"}`}>
        {!cur ? <div className="grid h-full place-items-center text-[#9aa7bc]">{t("guided.preview_empty")}</div>
          : cur.kind === "video"
            ? <video key={`${i}:${cur.rel}`} src={fileUrl(fileOf(base, cur.rel))} muted autoPlay={playing} playsInline className="h-full w-full object-cover" />
            : <img key={`${i}:${cur.rel}`} src={fileUrl(fileOf(base, cur.rel))} alt={cur.text} className="h-full w-full object-cover" />}
      </div>
      {frames.length > 0 && (
        <div className="mt-3 flex items-center gap-3">
          <button type="button" onClick={() => setPlaying(!playing)}
            className="flex h-12 shrink-0 items-center gap-2 rounded-full bg-[#69d7ff] px-5 text-base font-bold text-[#06111c]">
            {playing ? <><Pause size={20} /> {t("guided.pause")}</> : <><Play size={20} /> {t("guided.play")}</>}
          </button>
          <div className="flex min-w-0 flex-1 gap-1">
            {frames.map((f, n) => (
              <button key={`${n}:${f.rel}`} type="button" onClick={() => setAt(n)} aria-label={t("guided.jump_scene", { n: n + 1 })}
                className={`h-12 min-w-0 flex-1 overflow-hidden rounded-[4px] border-2 ${n === i ? "border-[#69d7ff]" : "border-transparent opacity-60"}`}>
                {f.kind === "image" ? <img src={fileUrl(fileOf(base, f.rel))} alt="" className="h-full w-full object-cover" />
                  : <video src={fileUrl(fileOf(base, f.rel))} muted preload="metadata" className="h-full w-full object-cover" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
