import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { LabPanel } from "./LabPanel"
import { errorKey, type Checks, type LabState, type Limits, type Model } from "./logic"
import { RemoveDialog } from "./RemoveDialog"
import { ResetDialog } from "./ResetDialog"
import { WizardView } from "./Wizard"

const POLL_MS = 3000

/** Modulseite Hydra-Labor (nur Admins): Assistent, bis das Labor fertig ist, danach die Labor-Seite. */
export function HydraLaborPage() {
  const { t } = useTranslation("hydralabor")
  const [s, setS] = useState<LabState | null>(null)
  const [checks, setChecks] = useState<Checks | null>(null)
  const [models, setModels] = useState<Model[]>([])
  const [model, setModel] = useState("")
  const [limits, setLimits] = useState<Limits>({ cpu: 2, ram_mb: 4096, disk_gb: 20 })
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [ask, setAsk] = useState<"" | "reset" | "remove">("")

  const load = useCallback(() => api.getState().then(setS).catch((e) => setMsg(errorKey(e))), [])
  useEffect(() => { load(); api.getModels().then((r) => setModels(r.items)).catch(() => {}) }, [load])
  // Nur abfragen, solange ein Vorgang läuft – sonst keine Dauerschleife.
  useEffect(() => {
    if (!s?.running) return
    const id = setTimeout(load, POLL_MS)
    return () => clearTimeout(id)
  }, [s, load])

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setMsg(null)
    try { await fn(); await load() } catch (e) { setMsg(errorKey(e)) } finally { setBusy(false) }
  }

  if (!s) return <div className="p-4 text-sm text-zinc-400">{msg ? t(msg) : "…"}</div>
  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
        <p className="text-sm text-zinc-400">{t("subtitle")}</p>
      </header>
      {s.step === "ready" && s.running !== "remove" ? (
        <LabPanel s={s} busy={busy} msg={msg} onJob={(j) => act(() => api.startJob(j))}
          onPower={(a) => act(() => api.power(a))} onAskReset={() => setAsk("reset")} onAskRemove={() => setAsk("remove")} />
      ) : (
        <WizardView s={s} checks={checks} models={models} model={model} limits={limits} busy={busy} msg={msg}
          onCheck={() => act(async () => setChecks(await api.runChecks(limits)))} onModel={setModel}
          onLimits={(l) => { setLimits(l); setChecks(null) }} onCreate={() => act(() => api.createLab(model, limits))} />
      )}
      {ask === "reset" && <ResetDialog busy={busy} onCancel={() => setAsk("")}
        onConfirm={() => { setAsk(""); act(() => api.startJob("reset")) }} />}
      {ask === "remove" && <RemoveDialog busy={busy} onCancel={() => setAsk("")}
        onConfirm={() => { setAsk(""); act(() => api.removeLab()) }} />}
    </div>
  )
}
