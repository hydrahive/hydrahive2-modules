import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Plus } from "lucide-react"
import { miningApi, type Rig } from "../api"
import { PairDialog } from "./PairDialog"
import { RigRow } from "./RigRow"

const POLL_MS = 15_000

export function RigsPanel({ canControl }: { canControl: boolean }) {
  const { t } = useTranslation("mining")
  const [rigs, setRigs] = useState<Rig[]>([])
  const [error, setError] = useState<string | null>(null)
  const [pairing, setPairing] = useState(false)
  const [tick, setTick] = useState(0)
  const reload = useCallback(() => setTick((n) => n + 1), [])

  useEffect(() => {
    if (!canControl) return
    let alive = true
    miningApi.rigs()
      .then((r) => { if (alive) { setRigs(r); setError(null) } })
      .catch((e) => { if (alive) setError(String(e)) })
    const id = window.setTimeout(reload, POLL_MS)
    return () => { alive = false; window.clearTimeout(id) }
  }, [canControl, tick, reload])

  const act = (p: Promise<unknown>) => { p.then(reload).catch((e) => setError(String(e))) }
  const confirmRevoke = (id: string) => { if (window.confirm(t("revoke_confirm"))) act(miningApi.revoke(id)) }

  if (!canControl) return null
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-200">{t("rigs_title")} ({rigs.filter((r) => r.status !== "revoked").length})</h2>
        {!pairing && (
          <button onClick={() => setPairing(true)}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-500">
            <Plus size={14} /> {t("pair_button")}
          </button>
        )}
      </div>
      {pairing && <PairDialog onDone={() => { setPairing(false); reload() }} />}
      {error && <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}
      {rigs.length === 0 ? (
        <p className="rounded-lg border border-white/10 p-4 text-sm text-zinc-400">{t("rigs_empty")}</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900/80 text-left text-xs uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="px-3 py-2">{t("col_rig")}</th><th className="px-3 py-2">{t("col_state")}</th>
                <th className="px-3 py-2">{t("gpu")}</th><th className="px-3 py-2 text-right">{t("col_temp")}</th>
                <th className="px-3 py-2 text-right">{t("col_power")}</th><th className="px-3 py-2 text-right">{t("col_load")}</th>
                <th className="px-3 py-2">{t("col_system")}</th><th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {rigs.map((r) => (
                <RigRow key={r.id} rig={r} canControl={canControl}
                  onApprove={(id) => act(miningApi.approve(id))} onRevoke={confirmRevoke}
                  onToggle={(id, en) => act(miningApi.setEnabled(id, en))} onRemove={(id) => act(miningApi.remove(id))} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
