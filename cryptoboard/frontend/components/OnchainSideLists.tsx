import { useTranslation } from "react-i18next"
import { UNKLAR_REASONS } from "../onchainImport"
import type { OnchainUnklar, OnchainWrap } from "../types"

const DIR_STYLE: Record<string, string> = { raus: "text-rose-400", rein: "text-emerald-400", fremd: "text-[#9aa7bc]" }

function shortHash(h: string): string {
  return h.length > 18 ? `${h.slice(0, 10)}…${h.slice(-6)}` : h
}

function Token({ symbol, direction, amount }: { symbol: string | null; direction: string; amount: string | null }) {
  const { t } = useTranslation("cryptoboard")
  return (
    <span className="inline-flex items-center gap-1 mr-3">
      <span className={DIR_STYLE[direction] ?? "text-[#9aa7bc]"}>{t(`oc_dir_${direction}`, { defaultValue: direction })}</span>
      <span className="tabular-nums text-[#c8d2df]">{amount ?? "?"}</span>
      <span className="font-mono uppercase text-[#e8eef8]">{symbol ?? "?"}</span>
    </span>
  )
}

// Nur Anzeige: Wraps (ETH↔WETH, kein Trade) und unklare Transaktionen (nicht geraten).
export function OnchainSideLists({ wraps, unklar }: { wraps: OnchainWrap[]; unklar: OnchainUnklar[] }) {
  const { t } = useTranslation("cryptoboard")
  const box = "rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-2.5 space-y-1.5"
  return (
    <>
      {wraps.length > 0 && (
        <details className={box}>
          <summary className="cursor-pointer text-xs font-medium text-[#c8d2df]">{t("oc_wraps")} ({wraps.length})</summary>
          <p className="text-[11px] text-[#9aa7bc]">{t("oc_wraps_hint")}</p>
          {wraps.map((w) => (
            <div key={w.hash} className="text-[11px]">
              <span className="text-[#9aa7bc] tabular-nums mr-2">{w.executed_at ?? "—"}</span>
              <span className="font-mono text-[#9aa7bc] mr-2">{shortHash(w.hash)}</span>
              {w.assets.map((a, i) => <Token key={i} symbol={a.symbol} direction={a.direction} amount={a.amount} />)}
            </div>
          ))}
        </details>
      )}
      {unklar.length > 0 && (
        <details className={box} open>
          <summary className="cursor-pointer text-xs font-medium text-amber-300">{t("oc_unklar")} ({unklar.length})</summary>
          <p className="text-[11px] text-[#9aa7bc]">{t("oc_unklar_hint")}</p>
          {unklar.map((u) => (
            <div key={u.hash} className="text-[11px] border-t border-[rgb(var(--hh-s-rand,42_54_75))] pt-1">
              <span className="text-[#9aa7bc] tabular-nums mr-2">{u.executed_at ?? "—"}</span>
              <span className="font-mono text-[#9aa7bc] mr-2">{shortHash(u.hash)}</span>
              <span className="text-amber-300">
                {UNKLAR_REASONS.includes(u.reason) ? t(`oc_reason_${u.reason}`) : u.reason}
              </span>
              <div className="mt-0.5">
                {u.tokens.map((tk, i) => <Token key={i} symbol={tk.symbol} direction={tk.direction} amount={tk.amount} />)}
              </div>
            </div>
          ))}
        </details>
      )}
    </>
  )
}
