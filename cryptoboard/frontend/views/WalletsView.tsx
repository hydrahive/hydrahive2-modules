import { ChevronDown, ChevronRight, Coins, Plus, ShieldCheck, Trash2, Wallet } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { rgbFor } from "@/shared/colors"
import { cryptoApi } from "../api"
import { AddressForm } from "../components/AddressForm"
import { fmtPrice, fmtQty } from "../format"
import type { WalletBalances, WalletTokenAgg } from "../types"

const C = rgbFor("/cryptoboard")
const VS = "eur"

function shorten(addr: string): string {
  return addr.length > 16 ? `${addr.slice(0, 8)}…${addr.slice(-6)}` : addr
}

/** Eine aggregierte Token-Zeile, aufklappbar zu den einzelnen Wallets. */
function TokenRow({ tok }: { tok: WalletTokenAgg }) {
  const { t } = useTranslation("cryptoboard")
  const [open, setOpen] = useState(false)
  const many = tok.wallets.length > 1

  return (
    <li className="py-2.5">
      <button
        onClick={() => many && setOpen((o) => !o)}
        className={`flex w-full items-center gap-2.5 text-left ${many ? "cursor-pointer" : "cursor-default"}`}
      >
        <span className="flex w-4 justify-center text-zinc-600">
          {many ? (open ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : null}
        </span>
        <span className="font-mono text-sm uppercase text-zinc-200">{tok.symbol}</span>
        {tok.verified && (
          <span title={t("wl_verified")} className="inline-flex items-center gap-0.5 rounded bg-emerald-500/15 px-1 py-0.5 text-[9px] font-medium text-emerald-300">
            <ShieldCheck size={10} /> {t("wl_verified")}
          </span>
        )}
        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-white/[6%] text-zinc-400 uppercase">{t(`wl_chain_${tok.chain}`)}</span>
        <span className="ml-auto text-right">
          <span className="block tabular-nums text-sm text-zinc-100">
            {tok.value_known ? fmtPrice(tok.value, VS) : <span className="text-zinc-500">{t("wl_value_unknown")}</span>}
          </span>
          <span className="block text-[11px] tabular-nums text-zinc-500">
            {fmtQty(tok.amount)}
            {many && ` · ${t(tok.wallets.length === 1 ? "wl_on_wallets" : "wl_on_wallets_plural", { count: tok.wallets.length })}`}
          </span>
        </span>
      </button>

      {open && many && (
        <ul className="mt-1.5 ml-6 space-y-0.5 border-l border-white/[6%] pl-3">
          {tok.wallets.map((w, i) => (
            <li key={i} className="flex items-center gap-2 text-[11px]">
              <span className="text-zinc-400">{w.label}</span>
              <span className="px-1 py-0.5 rounded text-[9px] bg-white/[5%] text-zinc-500 uppercase">{t(`wl_chain_${w.chain}`)}</span>
              <span className="ml-auto tabular-nums text-zinc-400">{fmtQty(w.amount)}</span>
              <span className="w-20 text-right tabular-nums text-zinc-300">
                {w.value != null ? fmtPrice(w.value, VS) : "—"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

export function WalletsView() {
  const { t } = useTranslation("cryptoboard")
  const [data, setData] = useState<WalletBalances | null>(null)
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await cryptoApi.walletBalances())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function del(id: number) {
    if (!window.confirm(t("wl_confirm_delete"))) return
    await cryptoApi.deleteWallet(id)
    await load()
  }

  if (loading && !data) return <p className="p-8 text-center text-sm text-zinc-500">{t("wl_loading")}</p>

  const tokens = data?.tokens ?? []
  const rows = data?.addresses ?? []
  const hasUnknown = tokens.some((tk) => !tk.value_known)

  return (
    <div className="p-5 space-y-4 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="rounded-xl border border-white/[6%] bg-white/[3%] px-4 py-3">
          <div className="text-xs text-zinc-500">{t("wl_total")}</div>
          <div className="mt-0.5 text-xl font-bold tabular-nums text-zinc-100">{fmtPrice(data?.total ?? 0, VS)}</div>
        </div>
        {!adding && (
          <button onClick={() => setAdding(true)}
            className="ml-auto flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[4%] text-sm text-zinc-300 hover:bg-white/[7%] transition-colors">
            <Plus size={15} /> {t("wl_add_title")}
          </button>
        )}
      </div>

      {adding && (
        <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4">
          <h3 className="text-sm font-semibold text-zinc-200 mb-3">{t("wl_add_title")}</h3>
          <AddressForm onSaved={() => { setAdding(false); void load() }} onCancel={() => setAdding(false)} />
        </div>
      )}

      {/* Token-zentrierte Hauptansicht — über alle Wallets aggregiert */}
      <CollapsibleBox boxId="cryptoboard-tokens" color={C} icon={<Coins size={14} />} title={t("wl_tokens")}>
        <div className="box-b">
          {tokens.length === 0 ? (
            <p className="py-6 text-center text-sm text-zinc-500">{rows.length === 0 ? t("wl_empty") : t("wl_tokens_empty")}</p>
          ) : (
            <>
              <ul className="divide-y divide-white/[4%]">
                {tokens.map((tk, i) => <TokenRow key={`${tk.symbol}-${i}`} tok={tk} />)}
              </ul>
              {hasUnknown && <p className="mt-3 text-[11px] text-zinc-600">{t("wl_unknown_hint")}</p>}
            </>
          )}
        </div>
      </CollapsibleBox>

      {/* Adress-Verwaltung (Hinzufügen/Löschen + Roh-Bestände pro Adresse) */}
      <CollapsibleBox boxId="cryptoboard-wallets" color={C} icon={<Wallet size={14} />} title={t("wl_addresses")}>
        <div className="box-b">
          {rows.length === 0 ? (
            <p className="py-6 text-center text-sm text-zinc-500">{t("wl_empty")}</p>
          ) : (
            <ul className="divide-y divide-white/[4%]">
              {rows.map((r) => (
                <li key={r.id} className="py-3 group">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-white/[6%] text-zinc-300 uppercase">{t(`wl_chain_${r.chain}`)}</span>
                    {r.label && <span className="text-sm text-zinc-200">{r.label}</span>}
                    <span className="text-[11px] text-zinc-500 font-mono">{shorten(r.address)}</span>
                    <button onClick={() => del(r.id)} aria-label="delete"
                      className="ml-auto p-1 text-zinc-600 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Trash2 size={14} />
                    </button>
                  </div>
                  {r.assets.length > 0 ? (
                    <div className="mt-1.5 pl-1 space-y-0.5">
                      {r.assets.map((a, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className="w-16 truncate font-mono uppercase text-zinc-400">{a.symbol}</span>
                          <span className="tabular-nums text-zinc-300">{fmtQty(a.amount)}</span>
                          <span className="ml-auto tabular-nums text-zinc-100">
                            {a.value != null ? fmtPrice(a.value, VS) : <span className="text-zinc-600">{t("wl_value_unknown")}</span>}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-1 pl-1 text-[11px] text-zinc-600">{t("wl_no_balance")}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </CollapsibleBox>

      <p className="text-[11px] text-zinc-600 px-1">{t("wl_disclaimer")}</p>
    </div>
  )
}
