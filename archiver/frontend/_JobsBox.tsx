import { Briefcase, Trash2 } from "lucide-react"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { JobCard } from "./_JobCard"
import { archiverApi, type ArchiveJob } from "./api"

interface Props {
  jobs: ArchiveJob[]
  onCancel: (id: number) => void
  onDelete: (id: number) => void
}

export function JobsBox({ jobs, onCancel, onDelete }: Props) {
  const runningCount = jobs.filter(j => j.status === "running").length
  const finishedCount = jobs.filter(j => j.status !== "running").length

  if (jobs.length === 0) return null

  function clearFinished() {
    const finished = jobs.filter(j => j.status !== "running")
    finished.forEach(j => {
      archiverApi.deleteJob(j.id).then(() => onDelete(j.id)).catch(() => {})
    })
  }

  return (
    <CollapsibleBox
      boxId="archiver.jobs"
      title="Jobs"
      icon={<Briefcase size={14} />}
      color="168 85 247"
      defaultCollapsed={false}
      headerRight={
        <div className="flex items-center gap-2">
          {runningCount > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-semibold">
              {runningCount} aktiv
            </span>
          )}
          {finishedCount > 1 && (
            <button
              onClick={clearFinished}
              title="Alle fertigen Einträge löschen"
              className="flex items-center gap-1 text-[10px] text-zinc-600 hover:text-rose-400 transition-colors"
            >
              <Trash2 size={11} />
              Alle löschen
            </button>
          )}
        </div>
      }
    >
      <div className="p-4 space-y-3">
        {jobs.map(j => (
          <JobCard
            key={j.id}
            job={j}
            onCancel={() => {
              archiverApi.cancelJob(j.id).catch(() => {})
              onCancel(j.id)
            }}
            onDelete={() => {
              archiverApi.deleteJob(j.id).then(() => onDelete(j.id)).catch(() => {})
            }}
          />
        ))}
      </div>
    </CollapsibleBox>
  )
}
