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
        <p className="text-xs text-zinc-500">
          Spiegelt den Projekt-Workspace auf das Laufwerk.
        </p>
        <select
          value={selectedProject}
          onChange={e => setSelectedProject(e.target.value)}
          className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500/50 [&>option]:bg-zinc-900"
        >
          <option value="">Quell-Projekt wählen…</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select
          value={selectedDriveDevice}
          onChange={e => setSelectedDriveDevice(e.target.value)}
          className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500/50 [&>option]:bg-zinc-900"
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
          className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-500/50"
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
