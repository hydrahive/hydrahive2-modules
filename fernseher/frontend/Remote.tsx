import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Minus, Plus, Power, Volume2, VolumeX } from "lucide-react"
import { getApps, getChannels, setChannel, setMute, setPower, setVolume, startApp, type TvStatus } from "./api"
import { errorKey, filterChannels, stepVolume } from "./logic"

const BTN = "flex min-h-11 items-center justify-center gap-1.5 rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-100 hover:bg-zinc-700 disabled:opacity-40"

/** Fernbedienung: Ein/Aus, Lautstärke, Stumm, Sender und Apps. Jede Aktion zeigt danach den echten Zustand. */
export function Remote({ status, onChange }: { status: TvStatus; onChange: (s: TvStatus) => void }) {
  const { t } = useTranslation("fernseher")
  const [channels, setChannels] = useState<{ number: number; name: string }[]>([])
  const [apps, setApps] = useState<{ name: string }[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const on = status.power === "on"
  const shown = filterChannels(channels, query)

  useEffect(() => {
    if (!on) return
    getChannels().then(setChannels).catch(() => {})
    getApps().then(setApps).catch(() => {})
  }, [on])

  const run = (fn: () => Promise<TvStatus | void>) => {
    setBusy(true); setMsg(null)
    fn().then((s) => { if (s) onChange(s) }).catch((e) => setMsg(t(errorKey(e)))).finally(() => setBusy(false))
  }

  return (
    <section className="space-y-4 rounded-xl border border-white/10 bg-zinc-900 p-4" data-tv-remote>
      <h2 className="text-xs uppercase tracking-wide text-zinc-500">{t("remote.heading")}</h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <button className={BTN} disabled={busy} onClick={() => run(() => setPower(!on))}>
          <Power size={16} /> {on ? t("remote.off") : t("remote.on")}
        </button>
        <button className={BTN} disabled={busy || !on} onClick={() => run(() => setVolume(stepVolume(-2)))}>
          <Minus size={16} /> {t("remote.quieter")}
        </button>
        <button className={BTN} disabled={busy || !on} onClick={() => run(() => setVolume(stepVolume(+2)))}>
          <Plus size={16} /> {t("remote.louder")}
        </button>
        <button className={BTN} disabled={busy || !on} onClick={() => run(() => setMute(!status.muted))}>
          {status.muted ? <Volume2 size={16} /> : <VolumeX size={16} />} {status.muted ? t("remote.unmute") : t("remote.mute")}
        </button>
      </div>
      {msg && <p role="alert" className="text-sm text-amber-300">{msg}</p>}
      {on && channels.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm text-zinc-300">{t("remote.channels")}</h3>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("remote.search")}
            aria-label={t("remote.search")} className="mb-2 w-full rounded border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" />
          {shown.length === 0 && <p className="text-sm text-zinc-400">{t("remote.no_match")}</p>}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {shown.map((c) => (
              <button key={`${c.number}-${c.name}`} disabled={busy} onClick={() => run(() => setChannel(String(c.number)))}
                className={`${BTN} justify-start ${status.channel?.name === c.name ? "ring-1 ring-emerald-400/60" : ""}`}>
                <span className="w-7 text-right text-xs text-zinc-500">{c.number}</span>
                <span className="truncate">{c.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      {on && apps.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm text-zinc-300">{t("remote.apps")}</h3>
          <div className="flex flex-wrap gap-2">
            {apps.map((a) => (
              <button key={a.name} disabled={busy} className={BTN} onClick={() => run(() => startApp(a.name).then(() => {}))}>
                {a.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
