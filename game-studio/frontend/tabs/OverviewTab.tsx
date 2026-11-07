import { FolderOpen, MessagesSquare, Share2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { TabProps } from "./registry"

const card = "rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-4"

export function OverviewTab({ project, onOpenAgent }: TabProps) {
  const { t } = useTranslation("gameStudio")
  const host = window.location.hostname
  const share = project.sharing.enabled ? `//${host}/${project.sharing.share_name}` : ""
  const rows: [string, string][] = [
    [t("workspace.overview.engine"), `${t(`engine.${project.engine}`)}${project.engine === "unreal" ? ` · ${project.engine_version}` : ""}`],
    [t("workspace.overview.genre"), project.genre || "–"],
    [t("workspace.overview.platform"), t(`platform.${project.target_platform}`)],
  ]

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <section className={card}>
        <h2 className="text-sm font-semibold text-[#e8eef8]">{t("workspace.overview.idea")}</h2>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#c8d2df]">{project.idea || "–"}</p>
        {(project.core_action || project.success_condition) && (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div><p className="text-[11px] font-medium text-[#9aa7bc]">{t("fields.coreAction")}</p><p className="mt-1 text-sm text-[#c8d2df]">{project.core_action || "–"}</p></div>
            <div><p className="text-[11px] font-medium text-[#9aa7bc]">{t("fields.success")}</p><p className="mt-1 text-sm text-[#c8d2df]">{project.success_condition || "–"}</p></div>
          </div>
        )}
        <button type="button" onClick={onOpenAgent} className="mt-5 inline-flex items-center gap-2 rounded-lg bg-[#69d7ff] px-4 py-2 text-sm font-semibold text-[#0d1420] hover:bg-[#9ee6ff]">
          <MessagesSquare size={15} aria-hidden="true" />{t("workspace.overview.askAgent")}
        </button>
      </section>
      <aside className="space-y-4">
        <section className={card}>
          <dl className="space-y-2 text-sm">
            {rows.map(([label, value]) => <div key={label} className="flex justify-between gap-3"><dt className="text-[#9aa7bc]">{label}</dt><dd className="text-right text-[#e8eef8]">{value}</dd></div>)}
          </dl>
        </section>
        {project.engine_project_path && (
          <section className={card}>
            <p className="flex items-center gap-2 text-xs font-semibold text-[#e8eef8]"><FolderOpen size={14} className="text-[#69d7ff]" aria-hidden="true" />{t("workspace.overview.projectFile")}</p>
            <p className="mt-2 break-all font-mono text-[11px] text-emerald-200">{project.engine_project_path}</p>
          </section>
        )}
        {share && (
          <section className={card}>
            <p className="flex items-center gap-2 text-xs font-semibold text-[#e8eef8]"><Share2 size={14} className="text-[#69d7ff]" aria-hidden="true" />{t("sharing.title")}</p>
            <p className="mt-2 break-all font-mono text-[11px] text-emerald-200">{share}</p>
            <p className="mt-1 text-[11px] text-[#9aa7bc]">{t("sharing.user")}: {project.sharing.user}</p>
          </section>
        )}
      </aside>
    </div>
  )
}
