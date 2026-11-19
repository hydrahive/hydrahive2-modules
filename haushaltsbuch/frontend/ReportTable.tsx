import type { ReactNode } from "react"

export interface Column<Row> { label: string; cell: (row: Row) => ReactNode; right?: boolean }

/** Tabellenalternative zu einem Diagramm – gleiche Zeilen, nur formatiert. */
export function ReportTable<Row>({ caption, columns, rows }: { caption: string; columns: Column<Row>[]; rows: Row[] }) {
  return <div className="overflow-x-auto"><table className="w-full text-sm">
    <caption className="sr-only">{caption}</caption>
    <thead><tr className="text-left text-xs text-[#9aa7bc]">{columns.map((col) => <th key={col.label} scope="col" className={`px-2 py-1.5 font-semibold ${col.right ? "text-right" : ""}`}>{col.label}</th>)}</tr></thead>
    <tbody className="divide-y divide-[rgb(var(--hh-s-rand,38_50_71))]">{rows.map((row, i) => <tr key={i} className="text-[#d4deeb]">{columns.map((col) => <td key={col.label} className={`px-2 py-1.5 ${col.right ? "text-right tabular-nums" : ""}`}>{col.cell(row)}</td>)}</tr>)}</tbody>
  </table></div>
}
