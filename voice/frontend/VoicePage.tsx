import { Mic, Settings2, Activity } from "lucide-react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"

/**
 * Voicebox — Etappe 1 (Gerüst).
 *
 * 3-Spalten-Layout wie die Buddy-Seite: links Einstellungen, Mitte der
 * Voice-Agent-Chat, rechts Status. In E1 sind alle drei Spalten Platzhalter;
 * E2/E3 füllen die Settings/Status, E4 den Chat.
 */
export function VoicePage() {
  const { t } = useTranslation("voice")

  return (
    <CockpitShell
      title="Voice"
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="/voice" context={t("subtitle")} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[300px_minmax(520px,1fr)_330px]">
        {/* Links: Einstellungen (E2/E3) */}
        <aside className="hidden min-h-0 overflow-y-auto xl:block">
          <Panel icon={<Settings2 size={14} />} title={t("settings_title")}>
            <p className="text-xs leading-4 text-[#8d9ab0]">{t("settings_hint")}</p>
          </Panel>
        </aside>

        {/* Mitte: Voice-Agent-Chat (E4) */}
        <main className="flex min-h-0 flex-col overflow-hidden rounded-[6px] border border-[#1c2636] bg-[#0a0f18]">
          <header className="flex items-center gap-2 border-b border-[#1c2636] px-4 py-3">
            <span className="grid h-8 w-8 place-items-center rounded-[4px] bg-[radial-gradient(circle_at_50%_20%,rgba(105,215,255,.3),rgba(8,11,17,.9))]">
              <Mic size={16} className="text-[#69d7ff]" />
            </span>
            <div>
              <div className="text-sm font-bold text-[#e8eef8]">{t("title")}</div>
              <div className="text-xs text-[#8d9ab0]">{t("subtitle")}</div>
            </div>
          </header>
          <div className="grid flex-1 place-items-center p-6 text-center">
            <div className="max-w-sm">
              <Mic size={40} className="mx-auto text-[#2a364b]" />
              <p className="mt-3 text-sm text-[#8d9ab0]">{t("chat_placeholder")}</p>
            </div>
          </div>
        </main>

        {/* Rechts: Status (E2) */}
        <aside className="hidden min-h-0 overflow-y-auto xl:block">
          <Panel icon={<Activity size={14} />} title={t("status_title")}>
            <p className="text-xs leading-4 text-[#8d9ab0]">{t("status_hint")}</p>
          </Panel>
        </aside>
      </div>
    </CockpitShell>
  )
}

function Panel({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-[6px] border border-[#1c2636] bg-[#0a0f18] p-3">
      <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[#69d7ff]">
        {icon}
        {title}
      </div>
      {children}
    </section>
  )
}
