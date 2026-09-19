import { AlertTriangle, CheckCircle2, Clock3, Inbox, UserRound } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { TicketDashboard } from "./api"

interface Props { summary: TicketDashboard | null }

export function OperationsSummary({ summary }: Props) {
  const { t } = useTranslation("tickets")
  if (!summary) return null
  const cards = [
    { label: t("dashboard.open"), value: summary.open + summary.triaged + summary.in_progress + summary.waiting, icon: Inbox, tone: "text-sky-300" },
    { label: t("dashboard.overdue"), value: summary.overdue, icon: AlertTriangle, tone: "text-orange-300" },
    { label: t("dashboard.dueSoon"), value: summary.due_soon, icon: Clock3, tone: "text-amber-300" },
    { label: t("dashboard.mine"), value: summary.mine, icon: UserRound, tone: "text-violet-300" },
    { label: t("dashboard.unassigned"), value: summary.unassigned, icon: CheckCircle2, tone: "text-emerald-300" },
  ]
  return <div className="grid grid-cols-2 gap-2 border-b border-[#1f2a3b] bg-[#0b131f] p-3 sm:grid-cols-5">
    {cards.map(({ label, value, icon: Icon, tone }) => <div key={label} className="rounded-[6px] border border-[#1f2a3b] bg-[#111b29] px-3 py-2"><div className={`mb-1 flex items-center gap-1.5 text-[10px] ${tone}`}><Icon size={12} />{label}</div><div className="text-lg font-semibold text-[#e8eef8]">{value}</div></div>)}
  </div>
}
