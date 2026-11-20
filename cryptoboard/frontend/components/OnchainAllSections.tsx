import { useTranslation } from "react-i18next"
import { errorKey } from "../onchainImport"
import { candKey, formatDelay, SPAM_GRUENDE, takenElsewhere, type Choice } from "../onchainAll"
import type { OnchainAddressStatus, OnchainMehrdeutig, OnchainSpam, OnchainXPair } from "../types"

const box = "rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-2.5 space-y-1.5"
const chip = "px-1 py-0.5 rounded text-[9px] bg-[rgb(var(--hh-s-innen,17_24_39))] text-[#c8d2df] uppercase"

function short(h: string): string {
  return h.length > 18 ? `${h.slice(0, 10)}…${h.slice(-6)}` : h
}

export function Delay({ seconds }: { seconds: number }) {
  const { t } = useTranslation("cryptoboard")
  const d = formatDelay(seconds)
  return <span className="text-sky-300">{t("oc_pairs_delay", { n: d.n, unit: t(`oc_unit_${d.unit}`) })}</span>
}

/** Kopfzeile eines Paars: beide Chains, Zeitpunkte und Verzögerung. */
export function PairHeader({ pair }: { pair: OnchainXPair }) {
  const { t } = useTranslation("cryptoboard")
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span className={chip}>{t("wl_chain_tron")}</span>
      <span className="tabular-nums">{pair.sell_at ?? "—"}</span>
      <span>→</span>
      <span className={chip}>{t(`wl_chain_${pair.evm_chain}`, { defaultValue: pair.evm_chain })}</span>
      <span className="tabular-nums">{pair.buy_at ?? "—"}</span>
      <Delay seconds={pair.delay_seconds} />
    </span>
  )
}

/** Status je Adresse: ok oder Fehler mit Klartext des Codes. */
export function AddressStatusList({ addresses }: { addresses: OnchainAddressStatus[] }) {
  const { t } = useTranslation("cryptoboard")
  return (
    <ul className="space-y-0.5 text-[11px]">
      {addresses.map((a) => {
        const key = a.error ? errorKey({ code: a.error }) : null
        return (
          <li key={a.id} className="flex flex-wrap items-center gap-2">
            <span className={chip}>{t(`wl_chain_${a.chain}`, { defaultValue: a.chain })}</span>
            <span className="text-[#c8d2df]">{a.label || short(a.address)}</span>
            {a.status === "ok"
              ? <span className="text-emerald-400">{t("oc_all_ok")}</span>
              : <span className="text-rose-400">{key ? t(key) : (a.error ?? t("oc_err_generic"))}</span>}
            {a.status === "ok" && a.truncated && <span className="text-amber-400">{t("oc_all_truncated")}</span>}
          </li>
        )
      })}
    </ul>
  )
}

/** Mehrdeutig: je TRX-Abgang die Kandidaten als Radio. Ohne Auswahl wird nichts gebucht. */
export function MehrdeutigList({ items, choice, onChoose }: {
  items: OnchainMehrdeutig[]; choice: Choice; onChoose: (m: OnchainMehrdeutig, key: string) => void
}) {
  const { t } = useTranslation("cryptoboard")
  if (items.length === 0) return null
  return (
    <section className={box}>
      <h4 className="text-xs font-medium text-amber-300">{t("oc_mehrdeutig_title")} ({items.length})</h4>
      <p className="text-[11px] text-[#9aa7bc]">{t("oc_mehrdeutig_hint")}</p>
      {items.map((m) => (
        <fieldset key={m.tron_tx} className="border-t border-[rgb(var(--hh-s-rand,42_54_75))] pt-1.5 space-y-1">
          <legend className="text-[11px] text-[#c8d2df]">
            <span className="tabular-nums text-[#9aa7bc] mr-2">{m.executed_at ?? "—"}</span>
            <span className="text-rose-400 mr-1">{t("tx_kind_sell")}</span>
            <span className="tabular-nums">{m.amount}</span> <span className="font-mono uppercase">{m.symbol}</span>
            <span className="ml-2 font-mono text-[#9aa7bc]">{short(m.tron_tx)}</span>
          </legend>
          {m.candidates.map((c) => {
            const k = candKey(c)
            const taken = takenElsewhere({ mehrdeutig: items }, choice, m.tron_tx, k)
            return (
              <label key={k} className={`flex flex-wrap items-center gap-2 text-[11px] ${taken ? "opacity-50" : ""}`}>
                <input type="radio" name={`md-${m.tron_tx}`} checked={choice[m.tron_tx] === k} disabled={taken}
                  onChange={() => onChoose(m, k)} />
                <span className={chip}>{t(`wl_chain_${c.evm_chain}`, { defaultValue: c.evm_chain })}</span>
                <span className="tabular-nums text-[#9aa7bc]">{c.executed_at ?? "—"}</span>
                <Delay seconds={c.delay_seconds} />
                <span className="text-emerald-400">{t("tx_kind_buy")}</span>
                <span className="tabular-nums text-[#c8d2df]">{c.amount}</span>
                <span className="font-mono uppercase text-[#e8eef8]">{c.symbol}</span>
                {taken && <span className="text-[#9aa7bc]">{t("oc_mehrdeutig_taken")}</span>}
              </label>
            )
          })}
          {choice[m.tron_tx] && (
            <button onClick={() => onChoose(m, "")} className="text-[10px] text-[#9aa7bc] hover:text-[#c8d2df]">
              {t("oc_mehrdeutig_reset")}
            </button>
          )}
        </fieldset>
      ))}
    </section>
  )
}

/** Vermutlicher Spam: eingeklappt, nur Anzeige, wird nie gebucht. */
export function SpamList({ items }: { items: OnchainSpam[] }) {
  const { t } = useTranslation("cryptoboard")
  if (items.length === 0) return null
  return (
    <details className={box}>
      <summary className="cursor-pointer text-xs font-medium text-[#c8d2df]">{t("oc_spam_title")} ({items.length})</summary>
      <p className="text-[11px] text-[#9aa7bc]">{t("oc_spam_hint")}</p>
      {items.map((s) => (
        <div key={s.hash} className="text-[11px] border-t border-[rgb(var(--hh-s-rand,42_54_75))] pt-1">
          <span className={`${chip} mr-2`}>{t(`wl_chain_${s.chain}`, { defaultValue: s.chain })}</span>
          <span className="text-[#9aa7bc] tabular-nums mr-2">{s.executed_at ?? "—"}</span>
          <span className="font-mono text-[#c8d2df] mr-2">{s.symbol}</span>
          <span className="tabular-nums text-[#9aa7bc] mr-2">{s.amount ?? "?"}</span>
          <span className="text-amber-300">
            {SPAM_GRUENDE.includes(s.grund) ? t(`oc_spam_${s.grund}`) : s.grund}
          </span>
        </div>
      ))}
    </details>
  )
}
