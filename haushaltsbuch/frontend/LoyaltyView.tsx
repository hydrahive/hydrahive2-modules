import { useCallback, useEffect, useState } from "react"
import { BadgePercent, ShoppingBasket } from "lucide-react"
import { AdminConfirmDialog } from "@/features/cockpit/admin/ui/AdminConfirmDialog"
import { errorMessage } from "./api"
import { LidlConnectDialog } from "./LidlConnectDialog"
import { LoyaltyConnectionCard } from "./LoyaltyConnectionCard"
import { loyaltyApi } from "./loyaltyApi"
import { LoyaltyReceipts } from "./LoyaltyReceipts"
import { LoyaltySyncHistory } from "./LoyaltySyncHistory"
import { PaybackBridgeDialog } from "./PaybackBridgeDialog"
import { PaybackData } from "./PaybackData"
import type { LoyaltyConnection, LoyaltyProvider, LoyaltySyncRun } from "./loyaltyTypes"
import { Button, ErrorState, LoadingState, panel } from "./ui"

const AVAILABLE: { provider: LoyaltyProvider; name: string; text: string; icon: typeof ShoppingBasket }[] = [
  { provider: "lidl_plus", name: "Lidl Plus", text: "Digitale Bons, Artikel, Rabatte und Pfand read-only synchronisieren.", icon: ShoppingBasket },
  { provider: "payback", name: "PAYBACK", text: "Punktestand, Verfall, Aktivitäten, Coupons und Partner manuell per Browser importieren.", icon: BadgePercent },
]

export function LoyaltyView({ onChanged }: { onChanged: () => void }) {
  const [connections, setConnections] = useState<LoyaltyConnection[]>()
  const [lidlEnabled, setLidlEnabled] = useState<boolean>()
  const [paybackEnabled, setPaybackEnabled] = useState<boolean>()
  const [busyId, setBusyId] = useState<number>()
  const [error, setError] = useState<unknown>()
  const [history, setHistory] = useState<{ id: number; runs: LoyaltySyncRun[] }>()
  const [deleteTarget, setDeleteTarget] = useState<LoyaltyConnection>()
  const [connectLidl, setConnectLidl] = useState(false)
  const [connectPayback, setConnectPayback] = useState(false)
  const [paybackConnectionId, setPaybackConnectionId] = useState<number>()
  const [receiptRefresh, setReceiptRefresh] = useState(0)
  const [paybackRefresh, setPaybackRefresh] = useState(0)

  const load = useCallback(() => {
    setError(undefined)
    Promise.all([loyaltyApi.connections(), loyaltyApi.providerStatus()])
      .then(([items, status]) => {
        setConnections(items)
        setLidlEnabled(status.lidl_plus.enabled)
        setPaybackEnabled(status.payback.enabled)
      })
      .catch(setError)
  }, [])
  useEffect(load, [load])

  async function sync(connection: LoyaltyConnection) {
    setBusyId(connection.id); setError(undefined)
    try {
      const result = await loyaltyApi.sync(connection.id)
      setConnections((items) => items?.map((item) => item.id === connection.id ? result.connection : item))
      if (connection.provider === "lidl_plus") setReceiptRefresh((value) => value + 1)
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
      if (paybackConnectionId === deleteTarget.id) setPaybackConnectionId(undefined)
      setDeleteTarget(undefined); setHistory(undefined); onChanged()
    } catch (cause) { setError(cause); setDeleteTarget(undefined) }
    finally { setBusyId(undefined) }
  }
  function upsertConnection(connection: LoyaltyConnection) {
    setConnections((items) => {
      const existing = items ?? []
      return existing.some((item) => item.id === connection.id)
        ? existing.map((item) => item.id === connection.id ? connection : item)
        : [...existing, connection]
    })
  }
  function connected(connection: LoyaltyConnection) {
    upsertConnection(connection)
    setConnectLidl(false); onChanged()
  }
  function paybackImported(connection?: LoyaltyConnection) {
    if (connection) {
      upsertConnection(connection)
      setPaybackConnectionId(connection.id)
    }
    load()
    setPaybackRefresh((value) => value + 1)
    onChanged()
  }

  if (connections === undefined || lidlEnabled === undefined || paybackEnabled === undefined) return <LoadingState label="Kundenkarten werden geladen …" />
  const hasLidl = connections.some((connection) => connection.provider === "lidl_plus")
  return <div className="space-y-5">
    <header><h2 className="text-lg font-bold text-[#e8eef8]">Kundenkarten</h2><p className="mt-1 text-sm text-[#8d9ab0]">Read-only Synchronisierung und bewusste Browser-Imports. Keine Passwörter im Haushaltsbuch, keine Couponaktivierung oder Punkteeinlösung.</p></header>
    {error !== undefined && <ErrorState error={errorMessage(error)} onRetry={load} />}
    {connections.length > 0 && <div className="grid gap-3 lg:grid-cols-2">{connections.map((connection) => <LoyaltyConnectionCard key={connection.id} connection={connection} busy={busyId === connection.id} onSync={() => sync(connection)} onHistory={() => showHistory(connection)} onImport={() => setConnectPayback(true)} onData={() => setPaybackConnectionId(connection.id)} onDelete={() => setDeleteTarget(connection)} />)}</div>}
    {history && <LoyaltySyncHistory runs={history.runs} onClose={() => setHistory(undefined)} />}
    {paybackConnectionId !== undefined && <PaybackData connectionId={paybackConnectionId} refreshKey={paybackRefresh} onClose={() => setPaybackConnectionId(undefined)} />}
    <section><h3 className="mb-2 text-sm font-bold text-[#dce5f2]">Verfügbare Anbieter</h3><div className="grid gap-3 md:grid-cols-2">{AVAILABLE.map((item) => {
      const Icon = item.icon
      const connectedProvider = connections.some((connection) => connection.provider === item.provider)
      const lidl = item.provider === "lidl_plus"
      const enabled = lidl ? lidlEnabled : paybackEnabled
      const openDialog = lidl ? () => setConnectLidl(true) : () => setConnectPayback(true)
      return <article key={item.provider} className={`${panel} p-4`}><div className="flex items-start gap-3"><Icon size={20} className="mt-0.5 text-cyan-200" /><div className="min-w-0 flex-1"><h4 className="font-bold text-[#e8eef8]">{item.name}</h4><p className="mt-1 text-xs text-[#8d9ab0]">{item.text}</p><p className={`mt-2 text-[11px] ${enabled ? "text-amber-200" : "text-[#718097]"}`}>{enabled ? lidl ? "Experimenteller, inoffizieller Testconnector ohne Stabilitätszusage." : "Experimentelle Browser-Bridge ohne Zugriff auf PAYBACK-Zugangsdaten." : "Vom Betreiber dieser Installation ausdrücklich deaktiviert."}</p></div></div><Button className="mt-3" tone={enabled ? "primary" : "default"} disabled={connectedProvider || !enabled} onClick={openDialog}>{connectedProvider ? "Bereits verbunden" : enabled ? lidl ? "Experimentell verbinden" : "Browser-Import starten" : "Verbindung nicht freigegeben"}</Button></article>
    })}</div></section>
    {hasLidl && <LoyaltyReceipts refreshKey={receiptRefresh} />}
    {connectLidl && <LidlConnectDialog onClose={() => setConnectLidl(false)} onConnected={connected} />}
    {connectPayback && <PaybackBridgeDialog onClose={() => setConnectPayback(false)} onConsumed={paybackImported} />}
    {deleteTarget && <AdminConfirmDialog title={`${deleteTarget.alias || deleteTarget.provider} trennen?`} confirmLabel={busyId ? "Wird getrennt …" : "Verbindung trennen"} cancelLabel="Abbrechen" confirmTone="danger" busy={busyId === deleteTarget.id} onClose={() => setDeleteTarget(undefined)} onConfirm={remove}>Die Verbindung und importierten Loyalty-Daten werden entfernt. {deleteTarget.provider === "lidl_plus" ? "Ein vom Lidl-Assistenten erzeugtes Credential wird ebenfalls aus dem Vault gelöscht. " : "Die lokal installierte Browser-Erweiterung bleibt unverändert. "}Ledger-Buchungen werden nicht verändert.</AdminConfirmDialog>}
  </div>
}
