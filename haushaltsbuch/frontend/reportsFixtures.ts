// Testdaten in der echten Server-Form (backend/reports.py): Minor-Units als Integer, Anteile in Basispunkten.
import type { BudgetReport, CashflowReport, CategoryReport, FixedCostReport, NetWorthReport } from "./types"

const frame = { range: "12" as const, currency: "EUR", start_month: "2026-10", end_month: "2026-11" }
export const cashflow: CashflowReport = { ...frame, report: "cashflow", totals: { income: 350000, expense: 120050, net: 229950 }, rows: [
  { month: "2026-10", income: 200000, expense: 70000, net: 130000 }, { month: "2026-11", income: 150000, expense: 50050, net: 99950 }] }
export const netWorth: NetWorthReport = { ...frame, report: "net-worth", totals: { start_balance: 100000, end_balance: 329950, change: 229950 }, rows: [
  { month: "2026-10", balance: 230000 }, { month: "2026-11", balance: 329950 }] }
export const categories: CategoryReport = { ...frame, report: "categories", totals: { expense: 100000 }, rows: [
  { category_id: 7, name: "Wohnen", amount: 60000, share_bp: 6000, has_children: true },
  { category_id: 9, name: "Essen", amount: 40000, share_bp: 4000, has_children: false }] }
export const budgets: BudgetReport = { ...frame, report: "budgets", totals: { planned: 50000, spent: 42000 }, rows: [
  { budget_id: 1, name: "Gesamtbudget", month: "2026-11", planned: 50000, spent: 42000, remaining: 8000, used_bp: 8400 }] }
export const fixedCosts: FixedCostReport = { ...frame, report: "fixed-costs", totals: { fixed: 80000, variable: 40050, total: 120050, fixed_bp: 6664 }, rows: [
  { month: "2026-11", fixed: 80000, variable: 40050, total: 120050, fixed_bp: 6664 }] }
