import { useTranslation } from "react-i18next"
import type { CSSProperties } from "react"
import { EmptyState } from "@/shared/EmptyState"
import leerBild from "../assets/leer.webp"

interface Column<T> {
  key: string
  label: string
  render?: (row: T) => React.ReactNode
}

interface Props<T> {
  rows: T[]
  columns: Column<T>[]
  emptyText?: string
}

export function ResourceTable<T extends Record<string, unknown>>({ rows, columns, emptyText }: Props<T>) {
  const { t } = useTranslation("akte")
  const empty = emptyText ?? t("akte.no_entries")
  if (rows.length === 0) {
    return <EmptyState src={leerBild} hint={empty} />
  }
  return (
    <div className="box overflow-hidden" style={{ "--c": "105 215 255" } as CSSProperties}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.5)]">
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-2 text-left text-xs font-medium text-[#9aa7bc] uppercase tracking-wider">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={String(row.id ?? i)} className="border-b border-[rgb(var(--hh-s-rand,42_54_75))] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] transition-colors">
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-3 text-[#c8d2df]">
                  {col.render ? col.render(row) : String(row[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
