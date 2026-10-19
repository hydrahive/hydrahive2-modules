import { Languages } from "lucide-react"
import { useTranslation } from "react-i18next"
import { languageChoices, type LanguageList } from "./translateLogic"

interface Props { list: LanguageList | null; value: string; busy: boolean; onChange: (lang: string) => void; onTranslate: () => void }

/** Reiter „Untertitel“, oben: welche Sprache bearbeitet wird, und „Übersetzen …“ (Spec 6c). */
export function SubtitleLanguagePick({ list, value, busy, onChange, onTranslate }: Props) {
  const { t } = useTranslation("studio")
  const choices = languageChoices(list, value)
  const current = choices.find((x) => x.language === value)
  return (
    <div className="flex items-center gap-1.5 border-b border-[#2a364b] px-2 py-1.5" data-sub-language>
      <select value={value} onChange={(e) => onChange(e.target.value)} disabled={busy} aria-label={t("sub_language_pick")}
        className="min-w-0 flex-1 rounded-[4px] border border-[#46617f] bg-[#111827] px-2 py-1 text-xs text-[#e8eef8] outline-none focus:border-[#69d7ff]">
        {choices.map((x) => (
          <option key={x.language} value={x.language}>
            {x.film ? t("sub_lang_film", { name: t(`lang.${x.language}`) }) : t("sub_lang_other", { name: t(`lang.${x.language}`), count: x.count })}
          </option>
        ))}
      </select>
      <button type="button" onClick={onTranslate} disabled={busy || !current?.count} data-sub-translate title={t("translate_hint")}
        className="flex shrink-0 items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-[11px] font-bold text-[#c3ccdd] hover:border-[#46617f] disabled:opacity-40">
        <Languages size={12} /> {t("translate_open")}
      </button>
    </div>
  )
}
