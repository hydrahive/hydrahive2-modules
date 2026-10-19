import { useTranslation } from "react-i18next"
import { LayoutDashboard } from "lucide-react"
import type { VitrineConfig } from "./api"
import { dashboardErrors, parseRepos } from "./rules"

const field = "rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-sm text-[#e8eef8]"
const DEFAULT = { tasks_user: "till", github_project: "Hydrahive DEV", github_repos: ["hydrahive/hydrahive2.0", "hydrahive/hydrahive2-modules"] }

/** Statuszentrale (S2): wessen Tasks, welches Projekt liefert den GitHub-Zugang (Token bleibt im Backend), welche Repos. */
export function DashboardCard({ config, onChange }: { config: VitrineConfig; onChange: (c: VitrineConfig) => void }) {
  const { t } = useTranslation("vitrine")
  const d = config.dashboard ?? DEFAULT
  const set = (patch: Partial<typeof d>) => onChange({ ...config, dashboard: { ...d, ...patch } })
  const errs = dashboardErrors(d)
  const cls = (k: string) => `${field} ${errs.includes(k) ? "border-rose-400" : ""}`
  return (
    <section className="space-y-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><LayoutDashboard size={15} className="text-[#69d7ff]" />{t("dash_title")}</h2>
      <p className="text-xs text-[#718097]">{t("dash_hint")}</p>
      <div className="grid gap-3 md:grid-cols-3">
        <label className="block text-xs text-[#8d9ab0]">{t("dash_tasks_user")}
          <input className={`${cls("tasks_user")} mt-1 w-full`} value={d.tasks_user} onChange={(e) => set({ tasks_user: e.target.value.trim() })} />
        </label>
        <label className="block text-xs text-[#8d9ab0]">{t("dash_github_project")}
          <input className={`${cls("github_project")} mt-1 w-full`} value={d.github_project} onChange={(e) => set({ github_project: e.target.value })} />
        </label>
        <label className="block text-xs text-[#8d9ab0]">{t("dash_github_repos")}
          <textarea rows={2} className={`${cls("github_repos")} mt-1 w-full`} value={d.github_repos.join("\n")}
            onChange={(e) => set({ github_repos: parseRepos(e.target.value) })} />
        </label>
      </div>
      {errs.length > 0 && <p className="text-xs text-rose-300">{t("dash_invalid")}</p>}
    </section>
  )
}
