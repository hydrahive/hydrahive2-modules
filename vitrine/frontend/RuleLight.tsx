import { useTranslation } from "react-i18next"
import { LIGHT_EFFECTS, lightColor, toPicker, type LightEffect } from "./light"
import type { Rule } from "./rules"

const field = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1.5 text-sm text-[#e8eef8]"

/** S8: Lichtfarbe + Effekt an einer Kalender-Regel (Teil von RuleEditor). Leer = Licht wie sonst. */
export function RuleLight({ rule, set }: { rule: Rule; set: (p: Partial<Rule>) => void }) {
  const { t } = useTranslation("vitrine")
  const on = !!rule.light_color
  return (
    <div className="md:col-span-2 flex flex-wrap items-center gap-2 text-xs text-[#9aa7bc]">
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={on} onChange={() => set(on ? { light_color: undefined, light_effect: undefined } : { light_color: "FF8800", light_effect: "static" })} />
        {t("rule_light")}
      </label>
      {on ? <>
        <input type="color" aria-label={t("light_color")} value={toPicker(rule.light_color ?? "")}
          onChange={(e) => set({ light_color: lightColor(e.target.value) ?? rule.light_color })} className="h-8 w-12 cursor-pointer rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-transparent" />
        <select aria-label={t("light_effect")} className={field} value={rule.light_effect ?? "static"} onChange={(e) => set({ light_effect: e.target.value as LightEffect })}>
          {LIGHT_EFFECTS.map((x) => <option key={x} value={x}>{t(`light_effect_${x}`)}</option>)}
        </select>
      </> : <span className="text-[#5b6b82]">{t("rule_light_none")}</span>}
    </div>
  )
}
