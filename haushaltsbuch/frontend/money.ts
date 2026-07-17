const currencyDigits = (currency: string, locale: string) =>
  new Intl.NumberFormat(locale, { style: "currency", currency }).resolvedOptions().maximumFractionDigits ?? 2

export function parseMinorUnits(input: string, currency: string, locale = navigator.language): number {
  const digits = currencyDigits(currency, locale)
  const parts = new Intl.NumberFormat(locale).formatToParts(12345.6)
  const decimal = parts.find((part) => part.type === "decimal")?.value ?? ","
  const group = parts.find((part) => part.type === "group")?.value ?? "."
  let value = input.trim().replace(/[\s\u00a0\u202f]/g, "")
  if (group) value = value.split(group).join("")
  if (decimal !== ".") value = value.replace(decimal, ".")
  if (!/^[+-]?\d+(?:\.\d+)?$/.test(value)) throw new Error("Bitte einen gültigen Betrag eingeben.")
  const negative = value.startsWith("-")
  const unsigned = value.replace(/^[+-]/, "")
  const [whole, fraction = ""] = unsigned.split(".")
  if (fraction.length > digits) throw new Error(`Maximal ${digits} Nachkommastellen sind erlaubt.`)
  const factor = 10n ** BigInt(digits)
  const minor = BigInt(whole) * factor + BigInt((fraction + "0".repeat(digits)).slice(0, digits) || "0")
  const signed = negative ? -minor : minor
  const result = Number(signed)
  if (!Number.isSafeInteger(result)) throw new Error("Der Betrag ist zu groß.")
  return result
}

export function formatMinorUnits(amount: number, currency: string, locale = navigator.language): string {
  if (!Number.isSafeInteger(amount)) return "—"
  const digits = currencyDigits(currency, locale)
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(amount / 10 ** digits)
}

export function minorToInput(amount: number, currency: string, locale = navigator.language): string {
  const digits = currencyDigits(currency, locale)
  const decimal = new Intl.NumberFormat(locale).formatToParts(1.1).find((part) => part.type === "decimal")?.value ?? ","
  const negative = amount < 0 ? "-" : ""
  const absolute = Math.abs(amount)
  const factor = 10 ** digits
  return `${negative}${Math.floor(absolute / factor)}${digits ? decimal + String(absolute % factor).padStart(digits, "0") : ""}`
}
