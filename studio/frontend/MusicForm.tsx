import { Loader2, Music } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { fieldCls, Label } from "./formParts"
import { jobText } from "./jobLogic"
import { MUSIC_MAX, MUSIC_MIN, type MusicDefaults, type MusicRequest } from "./musicLogic"
import type { Job } from "./planApi"
import { Backdrop } from "./StudioDialogs"

interface Props { defaults: MusicDefaults | null; job: Job | null; busy: boolean; onRun: (r: MusicRequest) => void; onClose: () => void }

/** „Musik erzeugen …“ im Reiter „Ton“ (Spec „Nachtrag 5c-2“): Ziel, Beschreibung, Länge, Modell, Kosten. */
export function MusicForm({ defaults, job, busy, onRun, onClose }: Props) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("music_title")}>
      <div className="flex items-center gap-2 border-b border-[#2a364b] px-4 py-2.5 text-sm font-black text-[#e8eef8]"><Music size={15} /> {t("music_title")}</div>
      {defaults ? <Body d={defaults} job={job} busy={busy} onRun={onRun} onClose={onClose} />
        : <p className="p-4 text-xs text-[#8d9ab0]">{t("loading")}</p>}
    </Backdrop>
  )
}

function Body({ d, job, busy, onRun, onClose }: { d: MusicDefaults } & Omit<Props, "defaults">) {
  const { t } = useTranslation("studio")
  const [target, setTarget] = useState("")
  const [text, setText] = useState(d.film.description)
  const [seconds, setSeconds] = useState(d.film.seconds)
  const pick = (id: string) => {
    const sc = d.scenes.find((s) => s.id === id)
    setTarget(id)
    setText(sc ? sc.description : d.film.description)
    setSeconds(sc ? sc.seconds : d.film.seconds)
  }
  const running = job?.status === "running" || job?.status === "queued"
  const valid = text.trim() !== "" && Number.isInteger(seconds) && seconds >= MUSIC_MIN && seconds <= MUSIC_MAX
  const error = jobText(t, job)
  return (
    <div className="flex flex-col gap-3 p-4 text-xs text-[#c3ccdd]">
      <label className="block"><Label>{t("music_target")}</Label>
        <select value={target} onChange={(e) => pick(e.target.value)} className={fieldCls} data-music-target>
          <option value="">{t("music_film")}</option>
          {d.scenes.map((s) => <option key={s.id} value={s.id}>{s.title || t("music_untitled")}</option>)}
        </select>
      </label>
      <label className="block"><Label>{t("music_description")}</Label>
        <textarea rows={4} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} placeholder={t("music_placeholder")}
          className={fieldCls} data-music-text />
      </label>
      <label className="block"><Label>{t("music_seconds")}</Label>
        <input type="number" min={MUSIC_MIN} max={MUSIC_MAX} step={1} value={seconds} onChange={(e) => setSeconds(Number(e.target.value))}
          className={`${fieldCls} w-28`} data-music-seconds />
      </label>
      <p className="text-[#8d9ab0]">{t("music_model", { model: d.model })} · {t("music_cost")}</p>
      {running && <p className="flex items-center gap-1.5 text-[#69d7ff]"><Loader2 size={12} className="animate-spin" /> {t("music_running")}</p>}
      {error && !running && <p className="text-[#ff6b8a]" role="alert">{error}</p>}
      <div className="flex justify-end gap-2 pt-1">
        <button type="button" onClick={onClose} className="rounded-[4px] border border-[#2a364b] px-3 py-1.5 font-bold text-[#c3ccdd] hover:border-[#46617f]">{t("music_close")}</button>
        <button type="button" disabled={busy || running || !valid} data-music-run
          onClick={() => onRun({ description: text.trim(), seconds, ...(target ? { scene_id: target } : {}) })}
          className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-40">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Music size={12} />} {t("music_run")}
        </button>
      </div>
    </div>
  )
}
