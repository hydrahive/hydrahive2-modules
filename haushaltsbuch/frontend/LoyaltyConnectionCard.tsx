import { Clock3, RefreshCw, ShieldAlert, Trash2 } from "lucide-react"
import type { LoyaltyConnection } from "./loyaltyTypes"
import { Button, panel } from "./ui"

const PROVIDER = { lidl_plus: "Lidl Plus", payback: "PAYBACK" }
const STATUS = {
  disconnected: "Getrennt",
  active: "Aktiv",
  syncing: "Synchronisiert …",
  reauth_required: "Neue Anmeldung erforderlich",
  blocked: "Vom Anbieter blockiert",
  disabled: "Deaktiviert",
  error: "Fehler",
}

export function LoyaltyConnectionCard({ connection, busy, onSync, onHistory, onDelete }: {
  connection: LoyaltyConnection
  busy: boolean
  onSync: () => void
  onHistory: () => void
  onDelete: () => void
}) {
  const canSync = connection.feature_enabled && connection.status === "active" && !busy
  const warning = connection.status === "reauth_required" || connection.status === "blocked" || connection.status === "error"
  return <article className={`${panel} p-4`}>
    <div className="flex flex-wrap items-start gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-bold text-[#e8eef8]">{connection.alias || PROVIDER[connection.provider]}</h3>
          <span className={`rounded border px-2 py-0.5 text-[11px] font-bold ${warning ? "border-amber-400/35 text-amber-200" : "border-emerald-400/35 text-emerald-200"}`}>{STATUS[connection.status]}</span>
        </div>
        <p className="mt-1 text-xs text-[#8d9ab0]">{PROVIDER[connection.provider]} · {connection.masked_account} · {connection.visibility === "household" ? "Im Haushalt sichtbar" : "Nur für Besitzer sichtbar"}</p>
        <p className="mt-2 text-[11px] text-[#718097]">Letzter Erfolg: {connection.last_success_at ? new Date(connection.last_success_at).toLocaleString("de-DE") : "Noch nie"}</p>
      </div>
      {warning && <ShieldAlert size={18} className="text-amber-200" />}
    </div>
    {!connection.feature_enabled && <p className="mt-3 rounded border border-cyan-400/20 bg-cyan-400/5 p-2 text-xs text-cyan-100">Der direkte Provider-Adapter ist noch nicht freigegeben. Die Verbindung bleibt sicher gespeichert, aber Synchronisierung ist deaktiviert.</p>}
    {connection.last_error_code && <p className="mt-2 text-xs text-rose-200">Letzter Fehler: {connection.last_error_code.replaceAll("_", " ")}</p>}
    <div className="mt-4 flex flex-wrap gap-2 border-t border-[#263247] pt-3">
      <Button tone="primary" disabled={!canSync} onClick={onSync}><RefreshCw size={13} className="mr-1 inline" />Jetzt synchronisieren</Button>
      <Button disabled={busy} onClick={onHistory}><Clock3 size={13} className="mr-1 inline" />Sync-Verlauf</Button>
      <Button tone="danger" disabled={busy} onClick={onDelete}><Trash2 size={13} className="mr-1 inline" />Trennen</Button>
    </div>
  </article>
}
