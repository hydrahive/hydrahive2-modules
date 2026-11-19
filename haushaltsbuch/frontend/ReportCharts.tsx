import { useId } from "react"
import { Area, AreaChart, Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { COLORS, axisTick, gridStroke, tooltipStyle } from "./chartShared"
import { compactMoney, monthLabel, moneyFormatter } from "./reportFormat"
import type { CashflowRow, NetWorthRow } from "./types"

interface Props<Row> { rows: Row[]; currency: string; mini?: boolean }

/** 1. Einnahmen/Ausgaben als Balken, Netto als Linie. `mini` = kleine Variante fürs Dashboard. */
export function CashflowChart({ rows, currency, mini = false }: Props<CashflowRow>) {
  const money = moneyFormatter(currency)
  return <ResponsiveContainer width="100%" height={mini ? 140 : 300}>
    <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
      <XAxis dataKey="month" tickFormatter={monthLabel} minTickGap={mini ? 24 : 12} tick={axisTick} axisLine={false} tickLine={false} />
      {!mini && <YAxis orientation="right" width={64} tickFormatter={(v) => compactMoney(Number(v), currency)} tick={axisTick} axisLine={false} tickLine={false} />}
      <Tooltip {...tooltipStyle} labelFormatter={(m) => monthLabel(String(m))} formatter={(value, name) => [money(Number(value)), String(name)]} />
      {!mini && <Legend wrapperStyle={{ fontSize: 12, color: "#9aa7bc" }} />}
      <Bar dataKey="income" name="Einnahmen" fill={COLORS.income} radius={[3, 3, 0, 0]} isAnimationActive={false} />
      <Bar dataKey="expense" name="Ausgaben" fill={COLORS.expense} radius={[3, 3, 0, 0]} isAnimationActive={false} />
      <Line type="monotone" dataKey="net" name="Netto" stroke={COLORS.net} strokeWidth={2} dot={false} isAnimationActive={false} />
    </ComposedChart>
  </ResponsiveContainer>
}

/** 2. Vermögensverlauf als Fläche (grün bei Zuwachs, rot bei Rückgang). */
export function NetWorthChart({ rows, currency, mini = false }: Props<NetWorthRow>) {
  const gid = useId().replace(/:/g, "")
  const money = moneyFormatter(currency)
  const positive = rows.length < 2 || rows[rows.length - 1].balance >= rows[0].balance
  const color = positive ? COLORS.income : COLORS.expense
  return <ResponsiveContainer width="100%" height={mini ? 140 : 300}>
    <AreaChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={0.35} /><stop offset="100%" stopColor={color} stopOpacity={0} /></linearGradient></defs>
      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
      <XAxis dataKey="month" tickFormatter={monthLabel} minTickGap={mini ? 24 : 12} tick={axisTick} axisLine={false} tickLine={false} />
      {!mini && <YAxis orientation="right" width={64} tickFormatter={(v) => compactMoney(Number(v), currency)} tick={axisTick} axisLine={false} tickLine={false} />}
      <Tooltip {...tooltipStyle} labelFormatter={(m) => monthLabel(String(m))} formatter={(value) => [money(Number(value)), "Vermögen"]} />
      <Area type="monotone" dataKey="balance" name="Vermögen" stroke={color} strokeWidth={2} fill={`url(#${gid})`} isAnimationActive={false} />
    </AreaChart>
  </ResponsiveContainer>
}
