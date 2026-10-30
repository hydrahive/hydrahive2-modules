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
    <section className="flex min-h-80 flex-col items-center justify-center rounded-xl border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.3)] px-6 text-center">
      <span className="relative rounded-2xl bg-[rgb(var(--hh-s-innen,17_24_39)/0.7)] p-4 text-[#9aa7bc]">
        <Icon size={28} />
        <Construction size={14} className="absolute -bottom-1 -right-1 text-amber-400" />
      </span>
      <h2 className="mt-5 text-base font-semibold text-[#e8eef8]">{t(`sections.${section}`)}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-[#9aa7bc]">{t("section_unavailable")}</p>
    </section>
  )
}
