import { useTranslation } from "react-i18next"
import { MUTED, input, panel } from "./ui"

export interface SelectableProject {
  id: string
  name: string
}

interface Props {
  projects: SelectableProject[]
  projectId: string
  status: "loading" | "ready" | "error"
  onChange: (id: string) => void
}

export function ProjectPicker({ projects, projectId, status, onChange }: Props) {
  const { t } = useTranslation("zerlegewerkstatt")
  return (
    <div className={panel}>
      <label className={`mb-1 block text-xs ${MUTED}`} htmlFor="zw-project">{t("project")}</label>
      {status === "error" ? (
        <p className="text-sm text-rose-400" role="alert">{t("projectsError")}</p>
      ) : status === "ready" && projects.length === 0 ? (
        <p className={`text-sm ${MUTED}`}>{t("projectsEmpty")}</p>
      ) : (
        <select
          id="zw-project"
          className={`${input} w-full`}
          value={projectId}
          disabled={status === "loading"}
          onChange={(event) => onChange(event.target.value)}
        >
          {status === "loading" && <option value="">{t("projectsLoading")}</option>}
          {projects.map((project) => (
            <option key={project.id} value={project.id}>{project.name}</option>
          ))}
        </select>
      )}
    </div>
  )
}
