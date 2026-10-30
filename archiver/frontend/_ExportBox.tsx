import { useState } from "react"
import { Upload, Play } from "lucide-react"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { archiverApi, type Drive, type ArchiveJob } from "./api"

interface Project { id: string; name: string }

interface Props {
  drives: Drive[]          // alle Drives; nur gemountete werden angezeigt
  projects: Project[]
  onJobStart: (job: ArchiveJob) => void
}

export function ExportBox({ drives, projects, onJobStart }: Props) {
  const [selectedProject, setSelectedProject] = useState("")
  const [selectedDriveDevice, setSelectedDriveDevice] = useState("")
  const [folderName, setFolderName] = useState("")
  const [starting, setStarting] = useState(false)

  const mountedDrives = drives.filter(d => d.mountpoint)
  const selectedDrive = mountedDrives.find(d => d.device === selectedDriveDevice) ?? null
  const canStart = !!(selectedProject && selectedDrive && folderName && !starting)

  async function handleStart() {
    if (!canStart || !selectedDrive) return
    setStarting(true)
    const driveTarget = `${selectedDrive.mountpoint}/${folderName}`
    try {
      const { id } = await archiverApi.startJob({
        drive_path: driveTarget,
        drive_label: selectedDrive.label,
        project_id: selectedProject,
        folder_name: folderName,
        direction: "export",
      })
      const newJob: ArchiveJob = {
        id, drive_label: selectedDrive.label,
        project_id: selectedProject, folder_name: folderName,
        target_path: driveTarget, direction: "export", status: "running", pct: 0,
        files_done: 0, files_total: 0, speed: "", error_count: 0, errors: [],
      }
      onJobStart(newJob)
    } finally {
      setStarting(false)
    }
  }

  return (
    <CollapsibleBox
      boxId="archiver.export"
      title="Exportieren"
      icon={<Upload size={14} />}
      color="16,185,129"
      defaultCollapsed
    >
      <div className="p-4 space-y-3">
        <p className="text-xs text-[#9aa7bc]">
          Spiegelt den Projekt-Workspace auf das Laufwerk.
        </p>
        <select
          value={selectedProject}
          onChange={e => setSelectedProject(e.target.value)}
          className="w-full rounded-lg bg-[rgb(var(--hh-s-box,21_28_43))] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8] focus:outline-none focus:border-emerald-500/50 [&>option]:bg-[rgb(var(--hh-s-box,21_28_43))]"
        >
          <option value="">Quell-Projekt wählen…</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select
          value={selectedDriveDevice}
          onChange={e => setSelectedDriveDevice(e.target.value)}
          className="w-full rounded-lg bg-[rgb(var(--hh-s-box,21_28_43))] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8] focus:outline-none focus:border-emerald-500/50 [&>option]:bg-[rgb(var(--hh-s-box,21_28_43))]"
        >
          <option value="">Ziellaufwerk wählen…</option>
          {mountedDrives.map(d => (
            <option key={d.device} value={d.device}>
              {d.label} ({d.mountpoint})
            </option>
          ))}
        </select>
        <input
          value={folderName}
          onChange={e => setFolderName(e.target.value)}
          placeholder="Zielordner auf Laufwerk, z.B. Backup_2026"
          className="w-full rounded-lg bg-[rgb(var(--hh-s-box,21_28_43))] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8] placeholder-[#9aa7bc] focus:outline-none focus:border-emerald-500/50"
        />
        <button
          onClick={handleStart}
          disabled={!canStart}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
        >
          <Play size={13} />
          {starting ? "Starte…" : "Projekt → HDD"}
        </button>
      </div>
    </CollapsibleBox>
  )
}
