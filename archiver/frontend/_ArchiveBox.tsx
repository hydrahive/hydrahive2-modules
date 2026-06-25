import { useState } from "react"
import { Download, Play } from "lucide-react"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { archiverApi, type Drive, type ArchiveJob } from "./api"

interface Project { id: string; name: string }

interface Props {
  selectedDrive: Drive | null
  projects: Project[]
  onJobStart: (job: ArchiveJob) => void
}

export function ArchiveBox({ selectedDrive, projects, onJobStart }: Props) {
  const [customPath, setCustomPath] = useState("")
  const [selectedProject, setSelectedProject] = useState("")
  const [folderName, setFolderName] = useState("")
  const [starting, setStarting] = useState(false)

  const drivePath = selectedDrive?.mountpoint || customPath
  const driveLabel = selectedDrive?.label || customPath || ""
  const canStart = !!(drivePath && selectedProject && folderName && !starting)

  async function handleStart() {
    if (!canStart) return
    setStarting(true)
    try {
      const { id } = await archiverApi.startJob({
        drive_path: drivePath,
        drive_label: driveLabel,
        project_id: selectedProject,
        folder_name: folderName,
        direction: "archive",
      })
      const newJob: ArchiveJob = {
        id, drive_label: driveLabel,
        project_id: selectedProject, folder_name: folderName,
        target_path: "", direction: "archive", status: "running", pct: 0,
        files_done: 0, files_total: 0, speed: "", error_count: 0, errors: [],
      }
      onJobStart(newJob)
    } finally {
      setStarting(false)
    }
  }

  return (
    <CollapsibleBox
      boxId="archiver.archive"
      title="Archivieren"
      icon={<Download size={14} />}
      color="138,92,246"
      defaultCollapsed={false}
    >
      <div className="p-4 space-y-3">
        {selectedDrive ? (
          <p className="text-xs text-zinc-500">
            Quelle: <span className="text-zinc-300">{selectedDrive.mountpoint}</span>
          </p>
        ) : (
          <input
            value={customPath}
            onChange={e => setCustomPath(e.target.value)}
            placeholder="Pfad manuell: /media/<user>/..."
            className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-violet-500/50"
          />
        )}
        <select
          value={selectedProject}
          onChange={e => setSelectedProject(e.target.value)}
          className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-violet-500/50 [&>option]:bg-zinc-900"
        >
          <option value="">Zielprojekt wählen…</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <input
          value={folderName}
          onChange={e => setFolderName(e.target.value)}
          placeholder="Unterordner-Name, z.B. HDD_2010_Blau"
          className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500/50"
        />
        <button
          onClick={handleStart}
          disabled={!canStart}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
        >
          <Play size={13} />
          {starting ? "Starte…" : "HDD → Projekt"}
        </button>
      </div>
    </CollapsibleBox>
  )
}
