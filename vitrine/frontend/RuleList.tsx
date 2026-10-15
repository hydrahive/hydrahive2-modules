import { useState } from "react"
import { useTranslation } from "react-i18next"
import { ChevronDown, ChevronRight, Plus, Trash2 } from "lucide-react"
import { describeRule, fromTemplate, newRule, ruleErrors, type Rule, type Template } from "./rules"
import { RuleEditor } from "./RuleEditor"
import type { VideoFile } from "./api"

export function RuleList({ rules, templates, videos, onChange }: {
  rules: Rule[]
  templates: Template[]
  videos: VideoFile[]
  onChange: (rules: Rule[]) => void
}) {
  const { t } = useTranslation("vitrine")
  const [open, setOpen] = useState<string | null>(null)
  const sorted = [...rules].sort((a, b) => b.priority - a.priority)
  const update = (r: Rule) => onChange(rules.map((x) => (x.id === r.id ? r : x)))
  const add = (r: Rule) => { onChange([...rules, r]); setOpen(r.id) }
  const have = new Set(rules.map((r) => r.name))

  return (
    <section className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-bold text-[#e8eef8]">{t("calendar")}</h2>
        <button type="button" onClick={() => add(newRule("range"))} className="ml-auto flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-xs text-[#c8d2df] hover:border-[#69d7ff]/50">
          <Plus size={13} />{t("rule_new")}
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {templates.filter((tpl) => !have.has(tpl.name)).map((tpl) => (
          <button key={tpl.name} type="button" onClick={() => add(fromTemplate(tpl))}
            className="rounded-full border border-[#2a364b] bg-[#151c2b] px-2.5 py-0.5 text-xs text-[#8d9ab0] hover:border-amber-300/50 hover:text-amber-200">
            + {tpl.name}
          </button>
        ))}
      </div>
      {sorted.length === 0
        ? <p className="rounded-[4px] border border-dashed border-[#2a364b] p-4 text-center text-xs text-[#718097]">{t("no_rules")}</p>
        : <ul className="divide-y divide-[#1c2638] rounded-[4px] border border-[#2a364b] bg-[#111827]">
            {sorted.map((r) => {
              const isOpen = open === r.id
              const invalid = ruleErrors(r).length > 0
              return (
                <li key={r.id}>
                  <div className="flex items-center gap-2 px-3 py-2 text-sm">
                    <button type="button" onClick={() => setOpen(isOpen ? null : r.id)} className="text-[#718097]" aria-label={t("edit")}>
                      {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                    <input type="checkbox" checked={r.enabled} onChange={() => update({ ...r, enabled: !r.enabled })} aria-label={t("enabled")} />
                    <span className={`font-semibold ${r.enabled ? "text-[#e8eef8]" : "text-[#5b6b82] line-through"}`}>{r.name || t("unnamed")}</span>
                    <span className="text-xs text-[#8d9ab0]">{describeRule(r, t)}</span>
                    <span className={`text-xs ${r.videos.length ? "text-[#69d7ff]" : "text-amber-300"}`}>{t("video_count", { count: r.videos.length })}</span>
                    {invalid && <span className="text-xs text-rose-300">!</span>}
                    <span className="ml-auto text-xs text-[#5b6b82]">{t("prio_short", { p: r.priority })}</span>
                    <button type="button" onClick={() => onChange(rules.filter((x) => x.id !== r.id))} className="rounded p-1 text-[#718097] hover:text-rose-300" aria-label={t("delete")}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                  {isOpen && <RuleEditor rule={r} videos={videos} onChange={update} />}
                </li>
              )
            })}
          </ul>}
    </section>
  )
}
