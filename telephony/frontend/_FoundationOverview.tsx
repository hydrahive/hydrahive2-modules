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
          <div key={label} className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-[#9aa7bc]">{label}</span>
              <Icon size={17} className={ready ? "text-emerald-400" : "text-[#9aa7bc]"} />
            </div>
            <p className="text-sm font-medium text-[#e8eef8]">{value}</p>
          </div>
        ))}
      </div>

      <section className="space-y-4 rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.4)] p-6">
        <ConnectionStatusBox status={status} />
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-2xl text-sm leading-6 text-[#c8d2df]">{t("setup_description")}</p>
          <button type="button" onClick={onSetup} data-voip-goto-settings="1"
            className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-[#163248] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#1b3d56]">
            <Settings2 size={16} />
            {registered ? t("setup_action_edit") : t("setup_action")}
          </button>
        </div>
      </section>

      <section className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32)/0.3)] p-5">
        <h2 className="text-sm font-semibold text-[#e8eef8]">{t("next_title")}</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {planned.map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-3 text-sm text-[#c8d2df]">
              <span className="rounded-lg bg-[rgb(var(--hh-s-innen,17_24_39)/0.7)] p-2 text-[#9aa7bc]"><Icon size={15} /></span>
              {text}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
