import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { PALETTE, tooltipStyle } from "./chartShared"
import { moneyFormatter, percentLabel } from "./reportFormat"
import type { CategoryReportRow } from "./types"

/** 3. Ausgabenverteilung als Ring. Klick (Sektor oder Listenzeile) auf eine Kategorie mit Unterkategorien öffnet diese. */
export function CategoryDonut({ rows, currency, onSelect }: { rows: CategoryReportRow[]; currency: string; onSelect: (row: CategoryReportRow) => void }) {
  const money = moneyFormatter(currency)
  return <div className="grid items-center gap-4 md:grid-cols-2">
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Tooltip {...tooltipStyle} formatter={(value, name) => [money(Number(value)), String(name)]} />
        <Pie data={rows} dataKey="amount" nameKey="name" innerRadius="55%" outerRadius="90%" paddingAngle={1} stroke="none" isAnimationActive={false}
          onClick={(_, index) => { const row = rows[index]; if (row?.has_children) onSelect(row) }}>
          {rows.map((row, i) => <Cell key={`${row.category_id}-${i}`} fill={PALETTE[i % PALETTE.length]} style={{ cursor: row.has_children ? "pointer" : "default" }} />)}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
    <ul className="space-y-1 text-sm">{rows.map((row, i) => <li key={`${row.category_id}-${i}`} className="flex items-center gap-2">
      <span className="h-3 w-3 shrink-0 rounded-sm" style={{ background: PALETTE[i % PALETTE.length] }} aria-hidden />
      {row.has_children
        ? <button type="button" onClick={() => onSelect(row)} className="min-w-0 flex-1 truncate text-left text-cyan-200 hover:underline" title="Unterkategorien anzeigen">{row.name} ›</button>
        : <span className="min-w-0 flex-1 truncate text-[#d4deeb]">{row.name}</span>}
      <span className="tabular-nums text-[#9aa7bc]">{percentLabel(row.share_bp)}</span>
      <strong className="w-28 text-right tabular-nums text-[#e8eef8]">{money(row.amount)}</strong>
    </li>)}</ul>
  </div>
}
