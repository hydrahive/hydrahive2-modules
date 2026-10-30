import { useState } from "react"
import { CheckCircle, XCircle, Loader2, Search, X } from "lucide-react"
import { archiverApi, type ArchiveJob, type WalletFile } from "./api"

function fmt(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M"
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "k"
  return String(n)
}

function WalletResult({ wallets }: { wallets: WalletFile[] }) {
  if (wallets.length === 0)
    return <p className="text-xs text-[#9aa7bc] mt-2">Keine Wallet-Dateien gefunden.</p>
  return (
    <div className="mt-2 space-y-1">
      <p className="text-xs text-amber-400 font-semibold">{wallets.length} Wallet-Datei(en) gefunden!</p>
      {wallets.map((w, i) => (
        <div key={i} className="text-xs text-[#c8d2df] pl-2 border-l border-amber-500/40">
          <span className="text-amber-300">{w.type}</span>
          {" — "}
          <span className="font-mono text-[#c8d2df]">{w.path}</span>
          <span className="text-[#9aa7bc] ml-2">({fmt(w.size_bytes)} B)</span>
        </div>
      ))}
    </div>
  )
}

export function JobCard({ job, onCancel, onDelete }: { job: ArchiveJob; onCancel?: () => void; onDelete?: () => void }) {
  const [wallets, setWallets] = useState<WalletFile[] | null>(null)
  const [scanning, setScanning] = useState(false)

  async function handleScan() {
    setScanning(true)
    try {
      const r = await archiverApi.scanWallets(job.id)
      setWallets(r.wallets)
    } finally {
      setScanning(false)
    }
  }

  const icon = job.status === "done"
    ? <CheckCircle size={14} className="text-emerald-400 flex-shrink-0" />
    : job.status === "failed"
    ? <XCircle size={14} className="text-rose-400 flex-shrink-0" />
    : job.status === "cancelled"
    ? <XCircle size={14} className="text-[#9aa7bc] flex-shrink-0" />
    : <Loader2 size={14} className="text-[#69d7ff] animate-spin flex-shrink-0" />

  const statusColor = job.status === "done" ? "bg-emerald-500"
    : job.status === "failed" ? "bg-rose-500"
    : job.status === "cancelled" ? "bg-[rgb(var(--hh-s-rand-hover,70_97_127))]"
    : "bg-[#163248]"

  return (
    <div className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-4 space-y-3">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-medium text-[#e8eef8] flex-1 truncate">
          {job.direction === "export"
            ? `${job.folder_name} → ${job.drive_label || "Drive"}`
            : `${job.drive_label || "Drive"} → ${job.folder_name}`}
        </span>
        {job.status === "running" && onCancel && (
          <button onClick={onCancel} title="Abbrechen"
            className="text-[#9aa7bc] hover:text-rose-400 transition-colors">
            <X size={14} />
          </button>
        )}
        {job.status !== "running" && onDelete && (
          <button onClick={onDelete} title="Eintrag löschen"
            className="text-[#9aa7bc] hover:text-[#c8d2df] transition-colors">
            <X size={14} />
          </button>
        )}
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-[11px] text-[#9aa7bc]">
          <span>{job.files_done} / {job.files_total || "?"} Dateien</span>
          <span>{job.speed || ""} {job.pct}%</span>
        </div>
        <div className="h-1.5 bg-[rgb(var(--hh-s-hebung,27_37_54))] rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all ${statusColor}`}
            style={{ width: `${job.pct}%` }} />
        </div>
      </div>

      {job.error_count > 0 && (
        <p className="text-[11px] text-amber-400">{job.error_count} Fehler/Warnungen (Permission denied etc.)</p>
      )}

      {job.status === "done" && (
        <div>
          <button onClick={handleScan} disabled={scanning}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 hover:bg-amber-500/20 disabled:opacity-40 transition-colors">
            <Search size={11} />
            {scanning ? "Scanne…" : "Nach Wallets suchen"}
          </button>
          {wallets !== null && <WalletResult wallets={wallets} />}
        </div>
      )}
    </div>
  )
}
