import { useCallback, useEffect, useState } from "react"
import { BadgePercent, ShoppingBasket } from "lucide-react"
import { AdminConfirmDialog } from "@/features/cockpit/admin/ui/AdminConfirmDialog"
import { errorMessage } from "./api"
import { LoyaltyConnectionCard } from "./LoyaltyConnectionCard"
import { loyaltyApi } from "./loyaltyApi"
import { LoyaltySyncHistory } from "./LoyaltySyncHistory"
import type { LoyaltyConnection, LoyaltyProvider, LoyaltySyncRun } from "./loyaltyTypes"
import { Button, ErrorState, LoadingState, panel } from "./ui"

const AVAILABLE: { provider: LoyaltyProvider; name: string; text: string; icon: typeof ShoppingBasket }[] = [
  { provider: "lidl_plus", name: "Lidl Plus", text: "Digitale Bons, Artikel, Rabatte und Pfand direkt synchronisieren.", icon: ShoppingBasket },
  { provider: "payback", name: "PAYBACK", text: "Punktestand, Verfall, Aktivitäten, Coupons und Partner synchronisieren.", icon: BadgePercent },
]

export function LoyaltyView({ onChanged }: { onChanged: () => void }) {
  const [connections, setConnections] = useState<LoyaltyConnection[]>()
  const [busyId, setBusyId] = useState<number>()
  const [error, setError] = useState<unknown>()
  const [history, setHistory] = useState<{ id: number; runs: LoyaltySyncRun[] }>()
  const [deleteTarget, setDeleteTarget] = useState<LoyaltyConnection>()

  const load = useCallback(() => {
    setError(undefined)
    loyaltyApi.connections().then(setConnections).catch(setError)
  }, [])
  useEffect(load, [load])

  async function sync(connection: LoyaltyConnection) {
    setBusyId(connection.id); setError(undefined)
    try {
      const result = await loyaltyApi.sync(connection.id)
      setConnections((items) => items?.map((item) => item.id === connection.id ? result.connection : item))
      onChanged()
    } catch (cause) { setError(cause) } finally { setBusyId(undefined) }
  }
  async function showHistory(connection: LoyaltyConnection) {
    setBusyId(connection.id); setError(undefined)
    try { setHistory({ id: connection.id, runs: await loyaltyApi.syncRuns(connection.id) }) }
    catch (cause) { setError(cause) } finally { setBusyId(undefined) }
  }
  async function remove() {
    if (!deleteTarget) return
    setBusyId(deleteTarget.id); setError(undefined)
    try {
      await loyaltyApi.remove(deleteTarget.id, deleteTarget.revision)
      setConnections((items) => items?.filter((item) => item.id !== deleteTarget.id))
      setDeleteTarget(undefined); setHistory(undefined); onChanged()
    } catch (cause) { setError(cause); setDeleteTarget(undefined) }
    finally { setBusyId(undefined) }
  }

  if (connections === undefined) return <LoadingState label="Kundenkarten werden geladen …" />
  return <div className="space-y-4">
    <header><h2 className="text-lg font-bold text-[#e8eef8]">Kundenkarten</h2><p className="mt-1 text-sm text-[#8d9ab0]">Direkte, read-only Synchronisierung. Keine Passwörter im Haushaltsbuch, keine automatische Couponaktivierung oder Punkteeinlösung.</p></header>
    {error !== undefined && <ErrorState error={errorMessage(error)} onRetry={load} />}
    {connections.length > 0 && <div className="grid gap-3 lg:grid-cols-2">{connections.map((connection) => <LoyaltyConnectionCard key={connection.id} connection={connection} busy={busyId === connection.id} onSync={() => sync(connection)} onHistory={() => showHistory(connection)} onDelete={() => setDeleteTarget(connection)} />)}</div>}
    {history && <LoyaltySyncHistory runs={history.runs} onClose={() => setHistory(undefined)} />}
    <section><h3 className="mb-2 text-sm font-bold text-[#dce5f2]">Verfügbare Anbieter</h3><div className="grid gap-3 md:grid-cols-2">{AVAILABLE.map((item) => { const Icon = item.icon; const connected = connections.some((connection) => connection.provider === item.provider); return <article key={item.provider} className={`${panel} p-4`}><div className="flex items-start gap-3"><Icon size={20} className="mt-0.5 text-cyan-200" /><div className="min-w-0 flex-1"><h4 className="font-bold text-[#e8eef8]">{item.name}</h4><p className="mt-1 text-xs text-[#8d9ab0]">{item.text}</p><p className="mt-2 text-[11px] text-amber-200">Experimenteller Provider: Verbindung erst nach technischem und rechtlichem Gate.</p></div></div><Button className="mt-3" disabled>{connected ? "Bereits verbunden" : "Verbindung noch nicht freigegeben"}</Button></article> })}</div></section>
    {deleteTarget && <AdminConfirmDialog title={`${deleteTarget.alias || deleteTarget.provider} trennen?`} confirmLabel={busyId ? "Wird getrennt …" : "Verbindung trennen"} cancelLabel="Abbrechen" confirmTone="danger" busy={busyId === deleteTarget.id} onClose={() => setDeleteTarget(undefined)} onConfirm={remove}>Die Provider-Verbindung und synchronisierten Loyalty-Daten werden entfernt. Das verschlüsselte Credential bleibt bestehen, bis du es im Vault löschst. Ledger-Buchungen werden nicht verändert.</AdminConfirmDialog>}
  </div>
}
