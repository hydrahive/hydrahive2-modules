import type { ComponentType } from "react"
import { useTranslation } from "react-i18next"
import { BookOpen, Gift, Landmark, ShoppingBag } from "lucide-react"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"

interface AreaCard {
  key: "transactions" | "bankImport" | "lidlPlus" | "payback"
  icon: ComponentType<{ size?: number; className?: string }>
  accent: string
}

const AREAS: AreaCard[] = [
  { key: "transactions", icon: BookOpen, accent: "text-emerald-300" },
  { key: "bankImport", icon: Landmark, accent: "text-sky-300" },
  { key: "lidlPlus", icon: ShoppingBag, accent: "text-amber-300" },
  { key: "payback", icon: Gift, accent: "text-violet-300" },
]

export function HaushaltsbuchPage() {
  const { t } = useTranslation("haushaltsbuch")

  return (
    <CockpitShell
      title={t("title")}
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="/haushaltsbuch" context={t("subtitle")} />
      <div className="min-h-0 flex-1 overflow-y-auto p-[10px]">
        <div className="mx-auto max-w-5xl space-y-6">
          <header>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black tracking-tight text-[#e8eef8]">{t("title")}</h1>
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300">
                {t("dummyBadge")}
              </span>
            </div>
            <p className="mt-1 text-sm text-[#8d9ab0]">{t("subtitle")}</p>
          </header>

          <div className="rounded-[6px] border border-amber-500/20 bg-amber-500/[6%] px-4 py-3 text-sm text-amber-200/90">
            {t("dummyNote")}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {AREAS.map((area) => {
              const Icon = area.icon
              return (
                <div
                  key={area.key}
                  className="flex items-start gap-4 rounded-[6px] border border-[#2a364b] bg-[#101724] p-4"
                >
                  <div className="rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-2.5">
                    <Icon size={20} className={area.accent} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h2 className="text-sm font-semibold text-[#e8eef8]">
                        {t(`areas.${area.key}.name`)}
                      </h2>
                      <span className="rounded-full bg-white/[6%] px-2 py-0.5 text-[10px] font-medium text-[#8d9ab0]">
                        {t("comingSoon")}
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-[#8d9ab0]">
                      {t(`areas.${area.key}.desc`)}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </CockpitShell>
  )
}
