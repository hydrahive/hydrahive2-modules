import { Briefcase } from "lucide-react"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { JobCard } from "./_JobCard"
import { archiverApi, type ArchiveJob } from "./api"

interface Props {
  jobs: ArchiveJob[]
  onCancel: (id: number) => void
}

export function JobsBox({ jobs, onCancel }: Props) {
  const runningCount = jobs.filter(j => j.status === "running").length

  if (jobs.length === 0) return null

  return (
    <CollapsibleBox
      boxId="archiver.jobs"
      title="Jobs"
      icon={<Briefcase size={14} />}
      color="168,85,247"
      defaultCollapsed={false}
      headerRight={
        runningCount > 0 ? (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-semibold">
            {runningCount} aktiv
          </span>
        ) : undefined
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
          />
        ))}
      </div>
    </CollapsibleBox>
  )
}
