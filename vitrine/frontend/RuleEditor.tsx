import { useTranslation } from "react-i18next"
import { newRule, ruleErrors, type Kind, type Rule, type Season } from "./rules"
import type { VideoFile } from "./api"
import { RuleFieldsExtra } from "./RuleFieldsExtra"
import { RuleLight } from "./RuleLight"

const field = "w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-sm text-[#e8eef8]"
const label = "block text-xs text-[#8d9ab0]"
const KINDS: Kind[] = ["range", "easter", "advent", "advent_sunday", "nth_weekday", "dates", "season", "time"]

/** Eine Regel bearbeiten (eingeklappt in der Liste, ausgeklappt = dieses Formular). */
export function RuleEditor({ rule, videos, onChange }: { rule: Rule; videos: VideoFile[]; onChange: (r: Rule) => void }) {
  const { t } = useTranslation("vitrine")
  const errs = ruleErrors(rule)
  const set = (patch: Partial<Rule>) => onChange({ ...rule, ...patch })
  const bad = (k: string) => (errs.includes(k) ? " border-rose-400/70" : "")
  const toggleVideo = (name: string) =>
    set({ videos: rule.videos.includes(name) ? rule.videos.filter((v) => v !== name) : [...rule.videos, name] })

  return (
    <div className="grid gap-3 border-t border-[#1c2638] p-3 md:grid-cols-2">
      <label className={label}>{t("name")}<input className={field + bad("name")} value={rule.name} onChange={(e) => set({ name: e.target.value })} /></label>
      <label className={label}>{t("kind_label")}
        <select className={field} value={rule.kind} onChange={(e) => set({ ...newRule(e.target.value as Kind), id: rule.id, name: rule.name, enabled: rule.enabled, priority: rule.priority, videos: rule.videos, light_color: rule.light_color, light_effect: rule.light_effect })}>
          {KINDS.map((k) => <option key={k} value={k}>{t(`kind.${k}`)}</option>)}
        </select>
      </label>

      {rule.kind === "range" && <>
        <label className={label}>{t("from_md")}<input className={field + bad("from")} placeholder="12-24" value={rule.from ?? ""} onChange={(e) => set({ from: e.target.value })} /></label>
        <label className={label}>{t("to_md")}<input className={field + bad("to")} placeholder="12-26" value={rule.to ?? ""} onChange={(e) => set({ to: e.target.value })} /></label>
      </>}
      {rule.kind === "time" && <>
        <label className={label}>{t("from_hm")}<input type="time" className={field + bad("from")} value={rule.from ?? ""} onChange={(e) => set({ from: e.target.value })} /></label>
        <label className={label}>{t("to_hm")}<input type="time" className={field + bad("to")} value={rule.to ?? ""} onChange={(e) => set({ to: e.target.value })} /></label>
      </>}
      {rule.kind === "easter" && <>
        <label className={label}>{t("offset_from")}<input type="number" className={field + bad("offset")} value={rule.offset_from ?? 0} onChange={(e) => set({ offset_from: Number(e.target.value) })} /></label>
        <label className={label}>{t("offset_to")}<input type="number" className={field + bad("offset")} value={rule.offset_to ?? 0} onChange={(e) => set({ offset_to: Number(e.target.value) })} /></label>
      </>}
      {rule.kind === "season" &&
        <label className={label}>{t("season_label")}
          <select className={field} value={rule.season} onChange={(e) => set({ season: e.target.value as Season })}>
            {(["spring", "summer", "autumn", "winter"] as Season[]).map((s) => <option key={s} value={s}>{t(`season.${s}`)}</option>)}
          </select>
        </label>}

      <RuleFieldsExtra key={rule.kind} rule={rule} errs={errs} set={set} />

      <RuleLight rule={rule} set={set} />

      <label className={label}>{t("priority")}<input type="number" min={0} max={100} className={field} value={rule.priority} onChange={(e) => set({ priority: Number(e.target.value) })} /></label>

      <fieldset className="md:col-span-2">
        <legend className={label}>{t("rule_videos")}</legend>
        {videos.length === 0
          ? <p className="text-xs text-[#718097]">{t("no_videos")}</p>
          : <div className="mt-1 flex flex-wrap gap-2">
              {videos.map((v) => (
                <label key={v.name} className="flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] px-2 py-1 text-xs text-[#c8d2df]">
                  <input type="checkbox" checked={rule.videos.includes(v.name)} onChange={() => toggleVideo(v.name)} />{v.name}
                </label>
              ))}
            </div>}
      </fieldset>
      {errs.length > 0 && <p className="text-xs text-rose-300 md:col-span-2">{t("rule_invalid")}</p>}
    </div>
  )
}
