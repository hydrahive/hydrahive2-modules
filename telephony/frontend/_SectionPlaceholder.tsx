import { Construction, type LucideIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { VoIPSection } from "./types"

interface SectionPlaceholderProps {
  section: VoIPSection
  icon: LucideIcon
}

export function SectionPlaceholder({ section, icon: Icon }: SectionPlaceholderProps) {
  const { t } = useTranslation("voip")

  return (
    <section className="flex min-h-80 flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-zinc-900/30 px-6 text-center">
      <span className="relative rounded-2xl bg-zinc-800/70 p-4 text-zinc-500">
        <Icon size={28} />
        <Construction size={14} className="absolute -bottom-1 -right-1 text-amber-400" />
      </span>
      <h2 className="mt-5 text-base font-semibold text-zinc-200">{t(`sections.${section}`)}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-zinc-500">{t("section_unavailable")}</p>
    </section>
  )
}
