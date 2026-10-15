import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { MonitorPlay, MoonStar, PlugZap, Sparkles } from "lucide-react"
import { vitrineApi, type VitrineStatus } from "./api"

const POLL_MS = 5000

/** Live-Vorschau (alle 10 s vom Dienst geschrieben) + Status. */
export function StatusCard() {
  const { t } = useTranslation("vitrine")
  const [st, setSt] = useState<VitrineStatus | null>(null)
  const [tick, setTick] = useState(() => Date.now())
  const [imgOk, setImgOk] = useState(true)

  useEffect(() => {
    let alive = true
    const load = () => {
      vitrineApi.status().then((s) => { if (alive) setSt(s) }).catch(() => {})
      setTick(Date.now())
    }
    load()
    const id = window.setInterval(load, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [])

  const state = !st ? "…" : !st.running ? t("state_stopped") : !st.connected ? t("state_no_display") : st.night ? t(`night_${st.night}`) : t("state_running")
  const tone = st?.running && st.connected ? "text-emerald-300" : "text-amber-300"
  return (
    <section className="grid gap-4 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4 md:grid-cols-[180px_1fr]">
      <div className="flex aspect-[9/16] w-[180px] items-center justify-center overflow-hidden rounded-[4px] border border-[#2a364b] bg-black">
        {imgOk
          ? <img src={vitrineApi.previewUrl(tick)} alt={t("preview")} className="h-full w-full object-cover" onError={() => setImgOk(false)} onLoad={() => setImgOk(true)} />
          : <MonitorPlay className="text-[#2a364b]" size={40} />}
      </div>
      <div className="space-y-2 text-sm">
        <p className={`flex items-center gap-2 font-bold ${tone}`}>{st?.night ? <MoonStar size={15} /> : <PlugZap size={15} />}{state}</p>
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-[#c8d2df]">
          <dt className="text-[#718097]">{t("video")}</dt><dd>{st?.video ?? "—"}</dd>
          <dt className="text-[#718097]">{t("rule")}</dt><dd>{st?.rule ?? t("rule_none")}</dd>
          {st?.holiday && <><dt className="text-[#718097]">{t("holiday")}</dt><dd className="flex items-center gap-1 text-amber-200"><Sparkles size={13} />{st.holiday}</dd></>}
          <dt className="text-[#718097]">{t("fps")}</dt><dd>{st?.fps ?? "—"}</dd>
          <dt className="text-[#718097]">{t("panel")}</dt><dd>{st?.size ? `${st.size[0]}×${st.size[1]}` : "—"}</dd>
        </dl>
        {st?.error && <p className="text-xs text-rose-300">{st.error}</p>}
      </div>
    </section>
  )
}
