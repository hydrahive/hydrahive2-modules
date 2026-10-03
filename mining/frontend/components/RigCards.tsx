import { useTranslation } from "react-i18next"
import type { GpuCard } from "../api"

const fmt = (v: number | null | undefined, unit: string) => (v === null || v === undefined ? "—" : `${Math.round(v)} ${unit}`)

/** Aufklappbare Liste der Karten eines Mehrkarten-Rigs (Temperatur, Watt, Last je Karte). */
export function RigCards({ cards }: { cards: GpuCard[] }) {
  const { t } = useTranslation("mining")
  if (cards.length < 2) return null
  return (
    <details className="mt-1 text-xs text-zinc-400">
      <summary className="cursor-pointer select-none text-zinc-500 hover:text-zinc-300">
        {t("cards_show", { n: cards.length })}
      </summary>
      <table className="mt-1 w-full">
        <tbody>
          {cards.map((c, i) => (
            <tr key={c.pci ?? i} className="border-t border-white/5">
              <td className="py-0.5 pr-2 text-zinc-500">#{i + 1}</td>
              <td className="py-0.5 pr-2 text-zinc-300">{c.gpu_model ?? "—"}</td>
              <td className="py-0.5 pr-2 text-right">{fmt(c.temp_c, "°C")}</td>
              <td className="py-0.5 pr-2 text-right">{fmt(c.power_w, "W")}</td>
              <td className="py-0.5 pr-2 text-right">{fmt(c.util_pct, "%")}</td>
              <td className="py-0.5 text-amber-300">{c.sensors && c.sensors !== "ok" ? t(`sensors_${c.sensors}`) : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  )
}
