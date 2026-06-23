import { Upload } from "lucide-react"
import { useCallback, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import type { ImportPreview } from "../types"
import { ImportPreviewTable } from "./ImportPreviewTable"

interface Props {
  onDone: (imported: number) => void
  onCancel: () => void
}

// CSV-Import-Flow: Datei wählen → Preview (Mapping anpassbar) → Commit.
export function ImportDialog({ onDone, onCancel }: Props) {
  const { t } = useTranslation("cryptoboard")
  const [csv, setCsv] = useState("")
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")
  const fileRef = useRef<HTMLInputElement>(null)

  const runPreview = useCallback(async (text: string, mapping?: Record<string, string | null>) => {
    setErr("")
    setBusy(true)
    try {
      setPreview(await cryptoApi.importPreview(text, mapping))
    } catch {
      setErr(t("imp_err_parse"))
      setPreview(null)
    } finally {
      setBusy(false)
    }
  }, [t])

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result || "")
      setCsv(text)
      void runPreview(text)
    }
    reader.readAsText(file)
  }

  function changeMapping(field: string, col: string) {
    if (!preview) return
    const mapping = { ...preview.mapping, [field]: col || null }
    void runPreview(csv, mapping)
  }

  async function commit() {
    if (!preview) return
    const toImport = preview.transactions
      .filter((tx) => tx.resolved && !tx.duplicate)
      .map((tx) => ({
        coin_id: tx.coin_id as string, symbol: tx.symbol, name: tx.coin_name || "",
        kind: tx.kind, quantity: tx.quantity, price: tx.price, fee: tx.fee,
        executed_at: tx.executed_at, hash: tx.hash,
      }))
    if (toImport.length === 0) { setErr(t("imp_nothing")); return }
    setBusy(true)
    try {
      const res = await cryptoApi.importCommit(toImport)
      onDone(res.imported)
    } catch {
      setErr(t("imp_err_commit"))
    } finally {
      setBusy(false)
    }
  }

  const importable = preview?.transactions.filter((tx) => tx.resolved && !tx.duplicate).length ?? 0
  const fieldCls = "px-2 py-1 rounded-md bg-zinc-900/70 border border-white/[8%] text-xs text-zinc-200 outline-none"

  return (
    <div className="space-y-3">
      {!preview && (
        <button onClick={() => fileRef.current?.click()}
          className="flex items-center gap-2 px-4 py-3 w-full justify-center rounded-lg border border-dashed border-white/15 text-sm text-zinc-300 hover:bg-white/[3%] transition-colors">
          <Upload size={16} /> {t("imp_choose_file")}
        </button>
      )}
      <input ref={fileRef} type="file" accept=".csv,text/csv,text/plain" onChange={onFile} className="hidden" />

      {busy && <p className="text-xs text-zinc-500 text-center py-2">{t("loading")}</p>}

      {preview && (
        <>
          {/* Mapping-Korrektur */}
          <div className="flex flex-wrap gap-2">
            {preview.fields.map((f) => (
              <label key={f} className="flex items-center gap-1 text-[11px] text-zinc-500">
                {t(`imp_field_${f}`)}
                <select value={preview.mapping[f] ?? ""} onChange={(e) => changeMapping(f, e.target.value)} className={fieldCls}>
                  <option value="">—</option>
                  {preview.header.map((h) => <option key={h} value={h}>{h}</option>)}
                </select>
              </label>
            ))}
          </div>

          {/* Hinweise */}
          <div className="flex flex-wrap gap-3 text-[11px]">
            <span className="text-emerald-400">{importable} {t("imp_ready")}</span>
            {preview.duplicate_count > 0 && <span className="text-zinc-500">{preview.duplicate_count} {t("imp_duplicate")}</span>}
            {preview.unresolved_symbols.length > 0 && <span className="text-amber-400">{t("imp_unresolved")}: {preview.unresolved_symbols.join(", ")}</span>}
            {preview.errors.length > 0 && <span className="text-rose-400">{preview.errors.length} {t("imp_skipped_rows")}</span>}
          </div>

          <ImportPreviewTable transactions={preview.transactions} />
        </>
      )}

      {err && <p className="text-xs text-rose-400">{err}</p>}

      <div className="flex items-center gap-2 pt-1">
        {preview && (
          <button disabled={busy || importable === 0} onClick={commit}
            className="px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-50">
            {t("imp_commit")} ({importable})
          </button>
        )}
        <button onClick={onCancel} className="px-4 py-2 rounded-lg bg-white/[4%] text-zinc-400 text-sm hover:text-zinc-200">
          {t("tx_cancel")}
        </button>
      </div>
    </div>
  )
}
