import { Select } from "./ui"

interface Named { budget_id: number; name: string }

/** Zeilen des gewählten Budgets; ohne (oder mit unbekannter) Auswahl das erste Budget. */
export function pickBudget<R extends { budget_id: number }>(rows: R[], id?: number): R[] {
  const wanted = id !== undefined && rows.some((r) => r.budget_id === id) ? id : rows[0]?.budget_id
  return rows.filter((r) => r.budget_id === wanted)
}

export function BudgetPicker({ rows, value, onChange }: { rows: Named[]; value?: number; onChange: (id: number) => void }) {
  const options = [...new Map(rows.map((r) => [r.budget_id, r.name])).entries()]
  if (options.length < 2) return null
  const current = options.some(([id]) => id === value) ? value : options[0][0]
  return <label className="grid gap-1 text-xs font-semibold text-[#b5c1d2]"><span>Budget</span>
    <Select value={current} onChange={(e) => onChange(Number(e.target.value))} aria-label="Budget auswählen">{options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</Select></label>
}
