import { useTranslation } from "react-i18next"
import type { GpuCard } from "../api"

const fmt = (v: number | null | undefined, unit: string) => (v === null || v === undefined ? "—" : `${Math.round(v)} ${unit}`)

/** Aufklappbare Liste der Karten eines Mehrkarten-Rigs (Temperatur, Watt, Last je Karte). */
export function RigCards({ cards }: { cards: GpuCard[] }) {
  const { t } = useTranslation("mining")
  if (cards.length < 2) return null
  return (
    <details className="mt-1 text-xs text-[#c8d2df]">
      <summary className="cursor-pointer select-none text-[#9aa7bc] hover:text-[#c8d2df]">
        {t("cards_show", { n: cards.length })}
      </summary>
      <table className="mt-1 w-full min-w-[22rem]">
        <thead className="text-[#9aa7bc]">
          <tr>
            <th className="py-0.5 pr-3 text-left font-normal">#</th>
            <th className="py-0.5 pr-3 text-left font-normal">{t("gpu")}</th>
            <th className="py-0.5 pr-3 text-right font-normal">{t("col_temp")}</th>
            <th className="py-0.5 pr-3 text-right font-normal">{t("col_power")}</th>
            <th className="py-0.5 pr-3 text-right font-normal">{t("col_load")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {cards.map((c, i) => (
            <tr key={c.pci ?? i} className="border-t border-[rgb(var(--hh-s-rand,42_54_75))]">
              <td className="py-0.5 pr-3 text-[#9aa7bc]">{i + 1}</td>
              <td className="py-0.5 pr-3 text-[#c8d2df]">{c.gpu_model ?? "—"}</td>
              <td className="py-0.5 pr-3 text-right tabular-nums">{fmt(c.temp_c, "°C")}</td>
              <td className="py-0.5 pr-3 text-right tabular-nums">{fmt(c.power_w, "W")}</td>
              <td className="py-0.5 pr-3 text-right tabular-nums">{fmt(c.util_pct, "%")}</td>
              <td className="whitespace-nowrap py-0.5 text-amber-300">{c.sensors && c.sensors !== "ok" ? t(`sensors_${c.sensors}`) : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  )
}
