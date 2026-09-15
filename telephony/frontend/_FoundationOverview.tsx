import {
  Archive,
  Bot,
  CheckCircle2,
  FolderKanban,
  LockKeyhole,
  Network,
  PhoneCall,
  Plus,
} from "lucide-react"
import { useTranslation } from "react-i18next"

interface FoundationOverviewProps {
  loaded: boolean
}

export function FoundationOverview({ loaded }: FoundationOverviewProps) {
  const { t } = useTranslation("voip")
  const cards = [
    { icon: CheckCircle2, label: t("status_module"), value: t("status_module_value"), ready: loaded },
    { icon: Network, label: t("status_connection"), value: t("status_connection_value"), ready: false },
    { icon: Bot, label: t("status_agent"), value: t("status_agent_value"), ready: false },
    { icon: Archive, label: t("status_archive"), value: t("status_archive_value"), ready: false },
  ]
  const planned = [
    { icon: FolderKanban, text: t("next_project") },
    { icon: Bot, text: t("next_agent") },
    { icon: PhoneCall, text: t("next_calls") },
    { icon: LockKeyhole, text: t("next_archive") },
  ]

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-100">
        {t("honest_notice")}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ icon: Icon, label, value, ready }) => (
          <div key={label} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</span>
              <Icon size={17} className={ready ? "text-emerald-400" : "text-zinc-600"} />
            </div>
            <p className="text-sm font-medium text-zinc-200">{value}</p>
          </div>
        ))}
      </div>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-2xl">
            <h2 className="text-base font-semibold text-zinc-100">{t("setup_title")}</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-400">{t("setup_description")}</p>
          </div>
          <div className="shrink-0 text-left sm:text-right">
            <button
              type="button"
              disabled
              title={t("setup_unavailable")}
              className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg bg-indigo-500/20 px-4 py-2.5 text-sm font-medium text-indigo-300 opacity-60"
            >
              <Plus size={16} />
              {t("setup_action")}
            </button>
            <p className="mt-2 max-w-56 text-xs text-zinc-600">{t("setup_unavailable")}</p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-950/30 p-5">
        <h2 className="text-sm font-semibold text-zinc-200">{t("next_title")}</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {planned.map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-3 text-sm text-zinc-400">
              <span className="rounded-lg bg-zinc-800/70 p-2 text-zinc-500"><Icon size={15} /></span>
              {text}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
