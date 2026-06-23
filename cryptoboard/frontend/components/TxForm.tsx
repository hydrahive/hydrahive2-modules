import { Search, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import type { SearchResult, Transaction, TxInput, TxKind } from "../types"

interface Props {
  initial?: Transaction | null   // gesetzt → Bearbeiten-Modus
  presetCoin?: { id: string; symbol: string; name: string } | null
  onSaved: () => void
  onCancel: () => void
}

const KINDS: TxKind[] = ["buy", "sell", "transfer_in", "transfer_out"]

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

// Manuelles Trade-Eingabeformular (Buy/Sell/Transfer). Kein Exchange-Zugriff —
// alle Werte trägt der Nutzer selbst ein. EUR als feste Währung.
export function TxForm({ initial, presetCoin, onSaved, onCancel }: Props) {
  const { t } = useTranslation("cryptoboard")
  const editing = !!initial
  const [coin, setCoin] = useState<{ id: string; symbol: string; name: string } | null>(
    initial ? { id: initial.coin_id, symbol: initial.symbol, name: initial.name } : presetCoin ?? null,
  )
  const [kind, setKind] = useState<TxKind>(initial?.kind ?? "buy")
  const [qty, setQty] = useState(initial ? String(initial.quantity) : "")
  const [price, setPrice] = useState(initial ? String(initial.price) : "")
  const [fee, setFee] = useState(initial ? String(initial.fee) : "")
  const [date, setDate] = useState(initial ? initial.executed_at.slice(0, 10) : todayIso())
  const [note, setNote] = useState(initial?.note ?? "")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  // Coin-Suche (nur im Neu-Modus ohne preset relevant)
  const [q, setQ] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const term = q.trim()
    if (term.length < 2) { setResults([]); return }
    const h = setTimeout(() => {
      cryptoApi.search(term).then((r) => { setResults(r.slice(0, 6)); setOpen(true) }).catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(h)
  }, [q])

  const isTransfer = kind === "transfer_in" || kind === "transfer_out"

  async function submit() {
    setErr("")
    if (!coin) { setErr(t("tx_err_coin")); return }
    const quantity = parseFloat(qty)
    if (!(quantity > 0)) { setErr(t("tx_err_qty")); return }
    const body: TxInput = {
      coin_id: coin.id, symbol: coin.symbol, name: coin.name, kind,
      quantity, price: parseFloat(price) || 0, fee: parseFloat(fee) || 0,
      executed_at: date, note: note.trim(),
    }
    setBusy(true)
    try {
      if (editing && initial) await cryptoApi.updateTx(initial.id, body)
      else await cryptoApi.addTx(body)
      onSaved()
    } catch {
      setErr(t("tx_err_save"))
    } finally {
      setBusy(false)
    }
  }

  const fieldCls = "w-full px-3 py-2 rounded-lg bg-zinc-900/70 border border-white/[8%] text-sm text-zinc-200 outline-none focus:border-white/20"

  return (
    <div className="space-y-3">
      {/* Coin */}
      {coin ? (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[4%] border border-white/[8%]">
          <span className="text-sm text-zinc-200 font-medium">{coin.name}</span>
          <span className="text-xs text-zinc-500 font-mono uppercase">{coin.symbol}</span>
          {!editing && (
            <button onClick={() => setCoin(null)} className="ml-auto text-zinc-600 hover:text-zinc-300"><X size={14} /></button>
          )}
        </div>
      ) : (
        <div ref={boxRef} className="relative">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-900/70 border border-white/[8%]">
            <Search size={15} className="text-zinc-500" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search_placeholder")}
              className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 outline-none" />
          </div>
          {open && results.length > 0 && (
            <div className="absolute z-30 mt-1 w-full rounded-lg bg-zinc-900 border border-white/10 shadow-xl overflow-hidden">
              {results.map((r) => (
                <button key={r.id} onClick={() => { setCoin({ id: r.id, symbol: r.symbol, name: r.name }); setOpen(false); setQ("") }}
                  className="flex items-center gap-2.5 w-full px-3 py-2 text-left hover:bg-white/[5%]">
                  {r.thumb && <img src={r.thumb} alt="" className="w-5 h-5 rounded-full" />}
                  <span className="text-sm text-zinc-200">{r.name}</span>
                  <span className="text-xs text-zinc-500 font-mono uppercase">{r.symbol}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Art */}
      <div className="grid grid-cols-4 gap-1.5">
        {KINDS.map((k) => (
          <button key={k} onClick={() => setKind(k)}
            className={`px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${kind === k ? "bg-white/10 text-white" : "bg-white/[3%] text-zinc-400 hover:text-zinc-200"}`}>
            {t(`tx_kind_${k}`)}
          </button>
        ))}
      </div>

      {/* Menge / Preis */}
      <div className="grid grid-cols-2 gap-2">
        <label className="space-y-1">
          <span className="text-xs text-zinc-500">{t("tx_quantity")}</span>
          <input type="number" step="any" value={qty} onChange={(e) => setQty(e.target.value)} className={fieldCls} placeholder="0.0" />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-zinc-500">{t("tx_price")} {isTransfer && <span className="text-zinc-600">({t("tx_optional")})</span>}</span>
          <input type="number" step="any" value={price} onChange={(e) => setPrice(e.target.value)} className={fieldCls} placeholder="0.00" />
        </label>
      </div>

      {/* Fee / Datum */}
      <div className="grid grid-cols-2 gap-2">
        <label className="space-y-1">
          <span className="text-xs text-zinc-500">{t("tx_fee")}</span>
          <input type="number" step="any" value={fee} onChange={(e) => setFee(e.target.value)} className={fieldCls} placeholder="0.00" />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-zinc-500">{t("tx_date")}</span>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={fieldCls} />
        </label>
      </div>

      {/* Notiz */}
      <label className="space-y-1 block">
        <span className="text-xs text-zinc-500">{t("tx_note")}</span>
        <input value={note} onChange={(e) => setNote(e.target.value)} className={fieldCls} maxLength={500} />
      </label>

      {err && <p className="text-xs text-rose-400">{err}</p>}

      <div className="flex items-center gap-2 pt-1">
        <button disabled={busy} onClick={submit}
          className="px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-50">
          {editing ? t("tx_save") : t("tx_add")}
        </button>
        <button onClick={onCancel} className="px-4 py-2 rounded-lg bg-white/[4%] text-zinc-400 text-sm hover:text-zinc-200">
          {t("tx_cancel")}
        </button>
      </div>
    </div>
  )
}
