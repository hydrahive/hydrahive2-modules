// Nur Darstellung: Beträge kommen als Minor-Units vom Server und werden hier nie summiert.
import { formatMinorUnits } from "./money"

const locale = () => navigator.language

export function monthLabel(month: string): string {
  const [year, mon] = month.split("-").map(Number)
  return new Date(year, mon - 1, 1).toLocaleDateString(locale(), { month: "short", year: "2-digit" })
}

/** Basispunkte (10000 = 100 %) als Prozentanzeige mit einer Nachkommastelle. */
export function percentLabel(basisPoints: number): string {
  return `${(basisPoints / 100).toLocaleString(locale(), { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`
}

/** Kurzform für Achsenbeschriftungen, z. B. „1,2 Tsd. €“. */
export function compactMoney(amount: number, currency: string): string {
  // Nachkommastellen der Währung OHNE notation: "compact" bestimmen – die Compact-Notation meldet
  // maximumFractionDigits 0 und würde Minor-Units sonst um Faktor 100 zu groß anzeigen.
  const digits = new Intl.NumberFormat(locale(), { style: "currency", currency }).resolvedOptions().maximumFractionDigits ?? 2
  return new Intl.NumberFormat(locale(), { style: "currency", currency, notation: "compact" }).format(amount / 10 ** digits)
}

export const moneyFormatter = (currency: string) => (amount: number) => formatMinorUnits(amount, currency)

export const RANGES = [
  { id: "3", label: "3 Monate" },
  { id: "6", label: "6 Monate" },
  { id: "12", label: "12 Monate" },
  { id: "24", label: "24 Monate" },
  { id: "all", label: "Seit Beginn" },
] as const

/** Zeitraum für Fließtext: „in den letzten 12 Monaten“ bzw. „seit Beginn“. */
export const rangeText = (range: string) => range === "all" ? "seit Beginn" : `in den letzten ${range} Monaten`
