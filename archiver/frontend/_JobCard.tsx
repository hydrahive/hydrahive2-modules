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
    return <p className="text-xs text-zinc-500 mt-2">Keine Wallet-Dateien gefunden.</p>
  return (
    <div className="mt-2 space-y-1">
      <p className="text-xs text-amber-400 font-semibold">{wallets.length} Wallet-Datei(en) gefunden!</p>
      {wallets.map((w, i) => (
        <div key={i} className="text-xs text-zinc-300 pl-2 border-l border-amber-500/40">
          <span className="text-amber-300">{w.type}</span>
          {" — "}
          <span className="font-mono text-zinc-400">{w.path}</span>
          <span className="text-zinc-600 ml-2">({fmt(w.size_bytes)} B)</span>
        </div>
      ))}
    </div>
  )
}

export function JobCard({ job, onCancel }: { job: ArchiveJob; onCancel?: () => void }) {
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
    ? <XCircle size={14} className="text-zinc-500 flex-shrink-0" />
    : <Loader2 size={14} className="text-violet-400 animate-spin flex-shrink-0" />

  const statusColor = job.status === "done" ? "bg-emerald-500"
    : job.status === "failed" ? "bg-rose-500"
    : job.status === "cancelled" ? "bg-zinc-600"
    : "bg-violet-500"

  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[3%] p-4 space-y-3">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-medium text-zinc-200 flex-1 truncate">
          {job.direction === "export"
            ? `${job.folder_name} → ${job.drive_label || "Drive"}`
            : `${job.drive_label || "Drive"} → ${job.folder_name}`}
        </span>
        {job.status === "running" && onCancel && (
          <button onClick={onCancel} title="Abbrechen"
            className="text-zinc-600 hover:text-rose-400 transition-colors">
            <X size={14} />
          </button>
        )}
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-[11px] text-zinc-500">
          <span>{job.files_done} / {job.files_total || "?"} Dateien</span>
          <span>{job.speed || ""} {job.pct}%</span>
        </div>
        <div className="h-1.5 bg-white/[8%] rounded-full overflow-hidden">
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
