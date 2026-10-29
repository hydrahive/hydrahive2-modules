import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { getStation, saveStation, skipTitle, startStation, stopStation } from "./api"
import { stationErrorKey, type Station, type StationSettings } from "./stationLogic"
import { StationView } from "./StationView"

export { StationView }

/** Reiter „Sender“: lädt den Stand alle 15 s neu; Knöpfe nur mit Freigabe (Backend prüft ohnehin). */
export function StationPanel() {
  const { t } = useTranslation("radiostream")
  const [s, setS] = useState<Station | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [rev, setRev] = useState(0)

  const load = useCallback(() => { getStation().then(setS).catch((e) => setMsg({ ok: false, text: t(stationErrorKey(e)) })) }, [t])
  useEffect(() => {
    load()
    const id = window.setInterval(load, 15000)
    return () => window.clearInterval(id)
  }, [load])

  const run = (fn: () => Promise<Station>, okKey: string) => {
    setBusy(true); setMsg(null)
    fn().then((n) => { setS(n); setRev((r) => r + 1); setMsg({ ok: true, text: t(okKey) }) })
      .catch((e) => setMsg({ ok: false, text: t(stationErrorKey(e)) }))
      .finally(() => setBusy(false))
  }
  if (!s) return <p className="text-sm text-zinc-400">{msg?.text ?? t("loading")}</p>
  return <StationView key={rev} s={s} busy={busy} msg={msg} host={window.location.host}
    onStart={() => run(startStation, "station.started")} onStop={() => run(stopStation, "station.stopped")}
    onSkip={() => run(skipTitle, "station.skipped")} onSave={(v: StationSettings) => run(() => saveStation(v), "station.saved")} />
}
