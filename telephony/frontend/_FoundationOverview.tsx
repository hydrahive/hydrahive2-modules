import { Archive, Bot, FolderKanban, LockKeyhole, Network, PhoneCall, PhoneIncoming, Settings2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ConnectionStatusBox } from "./_ConnectionStatus"
import type { ConnectionStatus } from "./types"

interface Props {
  status: ConnectionStatus
  onSetup: () => void
}

/** Übersicht: ehrlicher Stand (Verbindung echt, Anrufe/Agent/Archiv folgen) und Weg zur Einrichtung. */
export function FoundationOverview({ status, onSetup }: Props) {
  const { t } = useTranslation("voip")
  const registered = status === "registered"
  const cards = [
    { icon: Network, label: t("status_connection"), value: t(`conn.status.${status}.title`), ready: registered },
    { icon: PhoneIncoming, label: t("status_calls"), value: t("status_calls_value"), ready: false },
    { icon: Bot, label: t("status_agent"), value: t("status_agent_value"), ready: false },
    { icon: Archive, label: t("status_archive"), value: t("status_archive_value"), ready: false },
  ]
  const planned = [
    { icon: PhoneIncoming, text: t("next_inbound") },
    { icon: PhoneCall, text: t("next_outbound") },
    { icon: Bot, text: t("next_agent") },
    { icon: FolderKanban, text: t("next_project") },
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

      <section className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
        <ConnectionStatusBox status={status} />
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-2xl text-sm leading-6 text-zinc-400">{t("setup_description")}</p>
          <button type="button" onClick={onSetup} data-voip-goto-settings="1"
            className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-400">
            <Settings2 size={16} />
            {registered ? t("setup_action_edit") : t("setup_action")}
          </button>
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
