import { useState } from "react"
import { useTranslation } from "react-i18next"
import { listenerUrl, type Station, type StationSettings } from "./stationLogic"

interface Props {
  s: Station; busy: boolean; msg: { ok: boolean; text: string } | null; host: string
  onStart: () => void; onStop: () => void; onSkip: () => void; onSave: (v: StationSettings) => void
}
const BTN = "rounded border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] disabled:opacity-40"
const INPUT = "w-full rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-3 py-2 text-sm text-[#e8eef8]"

/** Anzeige des Senders – ohne Laden/Speichern (macht StationPanel), damit gut zu testen. */
export function StationView({ s, busy, msg, host, onStart, onStop, onSkip, onSave }: Props) {
  const { t } = useTranslation("radiostream")
  const [v, setV] = useState<StationSettings>(s.settings)
  const num = (k: keyof StationSettings) => (e: { target: { value: string } }) => setV({ ...v, [k]: Number(e.target.value) })
  const reachable = s.running && s.settings.reach !== "off"
  return (
    <div className="grid gap-6 lg:grid-cols-2" data-radiostream-station>
      <section className="space-y-4">
        <div className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-4">
          <p className={`text-xs font-semibold uppercase tracking-wide ${s.running ? "text-emerald-300" : "text-[#c8d2df]"}`}>
            {s.running ? t("station.on_air") : t("station.off")}</p>
          <p className="mt-2 text-lg font-semibold text-[#e8eef8] break-words">{s.now.title || "–"}</p>
          <p className="text-sm text-[#c8d2df] break-words">{s.now.artist}</p>
          {s.running && <p className="mt-2 text-sm text-[#c8d2df]">{t("station.listeners", { count: s.listeners })}</p>}
          {reachable && <a className="mt-2 inline-block text-sm text-emerald-300 underline" target="_blank" rel="noreferrer"
            href={listenerUrl(host, s.settings.listen_port)}>{t("station.open_page")}</a>}
        </div>
        {!s.installed && <p className="text-sm text-amber-300">{t("station.not_installed")}</p>}
        {s.can_control && s.installed && (
          <div className="flex flex-wrap gap-2">
            {s.running
              ? <>
                <button type="button" disabled={busy} onClick={onSkip} className={BTN}>{t("station.skip")}</button>
                <button type="button" disabled={busy} onClick={onStop} className={BTN}>{t("station.stop")}</button>
              </>
              : <button type="button" disabled={busy} onClick={onStart}
                className="rounded bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-500 disabled:opacity-40">{t("station.start")}</button>}
          </div>)}
        {msg && <p className={`text-sm ${msg.ok ? "text-emerald-300" : "text-rose-300"}`} role="status">{msg.text}</p>}
        <div>
          <h3 className="text-sm font-semibold text-[#c8d2df]">{t("station.recent")}</h3>
          {s.recent.length === 0 ? <p className="text-sm text-[#9aa7bc]">{t("station.recent_empty")}</p> : (
            <ol className="mt-1 space-y-1 text-sm text-[#c8d2df]">
              {s.recent.map((r) => <li key={`${r.track_id}-${r.played_at}`} className="break-words">{[r.artist, r.title].filter(Boolean).join(" – ")}</li>)}
            </ol>)}
        </div>
      </section>
      {s.can_control && (
        <section className="space-y-3">
          <h3 className="text-base font-semibold text-[#e8eef8]">{t("station.settings")}</h3>
          <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t("station.name")}</span>
            <input value={v.name} maxLength={80} onChange={(e) => setV({ ...v, name: e.target.value })} className={INPUT} /></label>
          <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t("station.subtitle_label")}</span>
            <input value={v.subtitle} maxLength={80} onChange={(e) => setV({ ...v, subtitle: e.target.value })} className={INPUT} /></label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t("station.artist_gap")}</span>
              <input type="number" min={0} max={1440} value={v.artist_gap_min} onChange={num("artist_gap_min")} className={INPUT} /></label>
            <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t("station.title_gap")}</span>
              <input type="number" min={0} max={60} value={v.title_gap_days} onChange={num("title_gap_days")} className={INPUT} /></label>
            <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t("station.port")}</span>
              <input type="number" min={1024} max={65535} value={v.listen_port} onChange={num("listen_port")} className={INPUT} /></label>
            <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t("station.max_listeners")}</span>
              <input type="number" min={1} max={1000} value={v.max_listeners} onChange={num("max_listeners")} className={INPUT} /></label>
          </div>
          <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t("station.reach")}</span>
            <select value={v.reach} onChange={(e) => setV({ ...v, reach: e.target.value as StationSettings["reach"] })} className={INPUT}>
              {(["all", "home", "off"] as const).map((r) => <option key={r} value={r}>{t(`station.reach_${r}`)}</option>)}
            </select></label>
          {v.reach === "all" && <p className="text-xs text-amber-300">{t("station.router_hint", { port: v.listen_port })}</p>}
          <button type="button" disabled={busy || !v.name.trim()} onClick={() => onSave(v)} className={BTN}>{t("station.save")}</button>
          {s.running && <p className="text-xs text-[#9aa7bc]">{t("station.save_hint")}</p>}
        </section>)}
    </div>
  )
}
