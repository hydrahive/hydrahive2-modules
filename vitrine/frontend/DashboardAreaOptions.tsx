import { useTranslation } from "react-i18next"
import type { AreaId, DashboardCfg } from "./dashLayout"
import { parseRepos, toggleIn } from "./dashLayout"

const field = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1 text-sm text-[#e8eef8]"

interface Props {
  id: AreaId
  d: DashboardCfg
  errs: string[]
  rooms: { rooms: string[]; available: boolean } | null
  set: (patch: Partial<DashboardCfg>) => void
}

/** Die wenigen Einstellungen je Bereich (Spec S4) – keine freien Texte auf der Seite am Gehäuse. */
export function DashboardAreaOptions({ id, d, errs, rooms, set }: Props) {
  const { t } = useTranslation("vitrine")
  const bad = (k: string) => (errs.includes(k) ? "border-rose-400" : "")
  if (id === "messages") return (
    <label className="flex items-center gap-2 text-xs text-[#9aa7bc]">{t("dash_messages_max")}
      <input type="number" min={1} max={5} className={`${field} w-16 ${bad("messages_max")}`} value={d.messages_max}
        onChange={(e) => set({ messages_max: Number(e.target.value) })} />
    </label>
  )
  if (id === "home") {
    if (!rooms) return <p className="text-xs text-[#9aa7bc]">…</p>
    if (!rooms.available) return <p className="text-xs text-[#9aa7bc]">{t("dash_home_unavailable")}</p>
    if (!rooms.rooms.length) return <p className="text-xs text-[#9aa7bc]">{t("dash_home_no_rooms")}</p>
    return (
      <div className="flex flex-wrap gap-3 text-xs text-[#c8d2df]">
        <span className="text-[#9aa7bc]">{d.home_rooms.length ? t("dash_home_some") : t("dash_home_all")}</span>
        {rooms.rooms.map((r) => (
          <label key={r} className="flex items-center gap-1">
            <input type="checkbox" checked={d.home_rooms.includes(r)} onChange={() => set({ home_rooms: toggleIn(d.home_rooms, r) })} />{r}
          </label>
        ))}
      </div>
    )
  }
  if (id === "tasks") return (
    <label className="flex items-center gap-2 text-xs text-[#9aa7bc]">{t("dash_tasks_user")}
      <input className={`${field} w-40 ${bad("tasks_user")}`} value={d.tasks_user} onChange={(e) => set({ tasks_user: e.target.value.trim() })} />
    </label>
  )
  if (id === "github") return (
    <div className="grid gap-2 md:grid-cols-2">
      <label className="block text-xs text-[#9aa7bc]">{t("dash_github_project")}
        <input className={`${field} mt-1 w-full ${bad("github_project")}`} value={d.github_project} onChange={(e) => set({ github_project: e.target.value })} />
      </label>
      <label className="block text-xs text-[#9aa7bc]">{t("dash_github_repos")}
        <textarea rows={2} className={`${field} mt-1 w-full ${bad("github_repos")}`} value={d.github_repos.join("\n")}
          onChange={(e) => set({ github_repos: parseRepos(e.target.value) })} />
      </label>
    </div>
  )
  if (id === "mining") return (
    <label className="flex items-center gap-2 text-xs text-[#c8d2df]">
      <input type="checkbox" checked={d.mining_in_machine} onChange={() => set({ mining_in_machine: !d.mining_in_machine })} />{t("dash_mining_in_machine")}
    </label>
  )
  return null
}
