import { useState } from "react"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import type { WalletChain } from "../types"

interface Props {
  onSaved: () => void
  onCancel: () => void
}

const CHAINS: WalletChain[] = ["base", "tron", "bitcoin"]

export function AddressForm({ onSaved, onCancel }: Props) {
  const { t } = useTranslation("cryptoboard")
  const [chain, setChain] = useState<WalletChain>("base")
  const [address, setAddress] = useState("")
  const [label, setLabel] = useState("")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  async function submit() {
    setErr("")
    if (!address.trim()) { setErr(t("wl_err_address")); return }
    setBusy(true)
    try {
      await cryptoApi.addWallet(chain, address.trim(), label.trim())
      onSaved()
    } catch {
      setErr(t("wl_err_invalid"))
    } finally {
      setBusy(false)
    }
  }

  const fieldCls = "w-full px-3 py-2 rounded-lg bg-zinc-900/70 border border-white/[8%] text-sm text-zinc-200 outline-none focus:border-white/20"

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-1.5">
        {CHAINS.map((c) => (
          <button key={c} onClick={() => setChain(c)}
            className={`px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${chain === c ? "bg-white/10 text-white" : "bg-white/[3%] text-zinc-400 hover:text-zinc-200"}`}>
            {t(`wl_chain_${c}`)}
          </button>
        ))}
      </div>
      <label className="space-y-1 block">
        <span className="text-xs text-zinc-500">{t("wl_address")}</span>
        <input value={address} onChange={(e) => setAddress(e.target.value)} className={`${fieldCls} font-mono text-xs`}
          placeholder={t(`wl_ph_${chain}`)} />
      </label>
      <label className="space-y-1 block">
        <span className="text-xs text-zinc-500">{t("wl_label")} <span className="text-zinc-600">({t("tx_optional")})</span></span>
        <input value={label} onChange={(e) => setLabel(e.target.value)} className={fieldCls} maxLength={60} />
      </label>
      {err && <p className="text-xs text-rose-400">{err}</p>}
      <div className="flex items-center gap-2 pt-1">
        <button disabled={busy} onClick={submit}
          className="px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-50">
          {t("wl_add")}
        </button>
        <button onClick={onCancel} className="px-4 py-2 rounded-lg bg-white/[4%] text-zinc-400 text-sm hover:text-zinc-200">
          {t("tx_cancel")}
        </button>
      </div>
    </div>
  )
}
