import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { dequeue, getExclude, getGenres, getQueue, getStation, moveQueue, saveExclude, saveStation, setProgram, skipTitle, startStation, stopStation, type Exclude } from "./api"
import { ExcludeBox } from "./ExcludeBox"
import { ProgramBox } from "./ProgramBox"
import { programErrorKey, type QueueItem } from "./programLogic"
import { QueueBox } from "./QueueBox"
import { useProgramData } from "./useProgramData"
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

  const { program, playlists, mixes, reload } = useProgramData()
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [ex, setEx] = useState<Exclude | null>(null)
  const [genres, setGenres] = useState<string[]>([])
  const load = useCallback(() => {
    getStation().then(setS).catch((e) => setMsg({ ok: false, text: t(stationErrorKey(e)) }))
    getQueue().then((r) => setQueue(r.items)).catch(() => {})
    reload()
  }, [t, reload])
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
  useEffect(() => {
    if (!s?.can_control) return
    getExclude().then(setEx).catch(() => {})
    getGenres().then((r) => setGenres(r.items.map((g) => g.genre))).catch(() => {})
  }, [s?.can_control])
  const change = (fn: () => Promise<unknown>) => {
    setBusy(true); setMsg(null)
    fn().then(() => load()).catch((e) => setMsg({ ok: false, text: t(programErrorKey(e)) })).finally(() => setBusy(false))
  }
  if (!s) return <p className="text-sm text-[#c8d2df]">{msg?.text ?? t("loading")}</p>
  return (
    <div className="space-y-6">
      <StationView key={rev} s={s} busy={busy} msg={msg} host={window.location.host}
        onStart={() => run(startStation, "station.started")} onStop={() => run(stopStation, "station.stopped")}
        onSkip={() => run(skipTitle, "station.skipped")} onSave={(v: StationSettings) => run(() => saveStation(v), "station.saved")} />
      <div className="grid gap-4 lg:grid-cols-2">
        {program && <ProgramBox p={program} playlists={playlists} mixes={mixes} busy={busy} onSet={(m, r) => change(() => setProgram(m, r))} />}
        <QueueBox items={queue} canModerate={!!program?.can_moderate} busy={busy}
          onMove={(id, pos) => change(() => moveQueue(id, pos))} onRemove={(id) => change(() => dequeue(id))} />
      </div>
      {s.can_control && ex && <ExcludeBox key={JSON.stringify(ex)} ex={ex} genres={genres} busy={busy}
        onSave={(r, l) => change(async () => { setEx(await saveExclude(r, l)); setMsg({ ok: true, text: t("exclude.saved") }) })} />}
    </div>
  )
}
