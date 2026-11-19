import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { COLORS, axisTick, gridStroke, tooltipStyle } from "./chartShared"
import { compactMoney, monthLabel, moneyFormatter, percentLabel } from "./reportFormat"
import type { BudgetReportRow, FixedCostRow } from "./types"

/** 4. Budget-Verlauf: Ist als Balken, Soll als Linie – für ein gewähltes Budget (Zeilen schon gefiltert). */
export function BudgetChart({ rows, currency }: { rows: BudgetReportRow[]; currency: string }) {
  const money = moneyFormatter(currency)
  return <ResponsiveContainer width="100%" height={300}>
    <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
      <XAxis dataKey="month" tickFormatter={monthLabel} minTickGap={12} tick={axisTick} axisLine={false} tickLine={false} />
      <YAxis orientation="right" width={64} tickFormatter={(v) => compactMoney(Number(v), currency)} tick={axisTick} axisLine={false} tickLine={false} />
      <Tooltip {...tooltipStyle} labelFormatter={(m) => monthLabel(String(m))} formatter={(value, name) => [money(Number(value)), String(name)]} />
      <Legend wrapperStyle={{ fontSize: 12, color: "#9aa7bc" }} />
      <Bar dataKey="spent" name="Ausgegeben (Ist)" fill={COLORS.net} radius={[3, 3, 0, 0]} isAnimationActive={false} />
      <Line type="stepAfter" dataKey="planned" name="Geplant (Soll)" stroke={COLORS.plan} strokeWidth={2} dot={false} isAnimationActive={false} />
    </ComposedChart>
  </ResponsiveContainer>
}

/** 5. Fest vs. variabel gestapelt, dazu der Festkosten-Anteil in % auf der rechten Achse. */
export function FixedCostChart({ rows, currency }: { rows: FixedCostRow[]; currency: string }) {
  const money = moneyFormatter(currency)
  return <ResponsiveContainer width="100%" height={300}>
    <ComposedChart data={rows} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}>
      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
      <XAxis dataKey="month" tickFormatter={monthLabel} minTickGap={12} tick={axisTick} axisLine={false} tickLine={false} />
      <YAxis yAxisId="geld" orientation="left" width={64} tickFormatter={(v) => compactMoney(Number(v), currency)} tick={axisTick} axisLine={false} tickLine={false} />
      <YAxis yAxisId="anteil" orientation="right" width={48} domain={[0, 10000]} tickFormatter={(v) => `${Number(v) / 100} %`} tick={axisTick} axisLine={false} tickLine={false} />
      <Tooltip {...tooltipStyle} labelFormatter={(m) => monthLabel(String(m))} formatter={(value, name) => [name === "Anteil Fixkosten" ? percentLabel(Number(value)) : money(Number(value)), String(name)]} />
      <Legend wrapperStyle={{ fontSize: 12, color: "#9aa7bc" }} />
      <Bar yAxisId="geld" stackId="kosten" dataKey="fixed" name="Fixkosten" fill={COLORS.fixed} isAnimationActive={false} />
      <Bar yAxisId="geld" stackId="kosten" dataKey="variable" name="Variable Kosten" fill={COLORS.variable} radius={[3, 3, 0, 0]} isAnimationActive={false} />
      <Line yAxisId="anteil" type="monotone" dataKey="fixed_bp" name="Anteil Fixkosten" stroke={COLORS.share} strokeWidth={2} dot={false} isAnimationActive={false} />
    </ComposedChart>
  </ResponsiveContainer>
}
