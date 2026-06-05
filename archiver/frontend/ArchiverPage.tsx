import { useEffect, useState } from "react"
import { HardDrive, RefreshCw, Play } from "lucide-react"
import { archiverApi, type Drive, type ArchiveJob } from "./api"
import { JobCard } from "./_JobCard"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface Project { id: string; name: string }

function useDrives() {
  const [drives, setDrives] = useState<Drive[]>([])
  const [loading, setLoading] = useState(false)
  async function refresh() {
    setLoading(true)
    try { setDrives(await archiverApi.drives()) } finally { setLoading(false) }
  }
  useEffect(() => { refresh() }, [])
  return { drives, loading, refresh }
}

function useProjects() {
  const [projects, setProjects] = useState<Project[]>([])
  useEffect(() => {
    const token = useAuthStore.getState().token ?? ""
    const h = token ? { Authorization: `Bearer ${token}` } : undefined
    fetch("/api/projects", { headers: h })
      .then(r => r.ok ? r.json() : [])
      .then((data: { projects?: Project[] } | Project[]) => {
        const list = Array.isArray(data) ? data : (data.projects ?? [])
        setProjects(list)
      })
      .catch(() => {})
  }, [])
  return projects
}

export function ArchiverPage() {
  const { drives, loading: drvLoading, refresh } = useDrives()
  const projects = useProjects()
  const [jobs, setJobs] = useState<ArchiveJob[]>([])

  // Form state
  const [selectedDrive, setSelectedDrive] = useState<Drive | null>(null)
  const [customPath, setCustomPath] = useState("")
  const [selectedProject, setSelectedProject] = useState("")
  const [folderName, setFolderName] = useState("")
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    archiverApi.jobs().then(setJobs).catch(() => {})
  }, [])

  const activeDrive = selectedDrive ?? (customPath ? { mountpoint: customPath, label: customPath, name: "", size: "", transport: "" } : null)

  async function handleStart() {
    if (!activeDrive || !selectedProject || !folderName) return
    setStarting(true)
    try {
      const { id } = await archiverApi.startJob({
        drive_path: activeDrive.mountpoint,
        drive_label: activeDrive.label || folderName,
        project_id: selectedProject,
        folder_name: folderName,
      })
      const newJob: ArchiveJob = {
        id, drive_label: activeDrive.label || folderName,
        project_id: selectedProject, folder_name: folderName,
        target_path: "", status: "running", pct: 0,
        files_done: 0, files_total: 0, speed: "", error_count: 0, errors: [],
      }
      setJobs(prev => [newJob, ...prev])
      const unsub = archiverApi.streamJob(id,
        (upd) => setJobs(prev => prev.map(j => j.id === id ? { ...j, ...upd } : j)),
        () => unsub(),
      )
    } finally {
      setStarting(false)
    }
  }

  function handleDriveSelect(d: Drive) {
    setSelectedDrive(d)
    setCustomPath("")
    if (!folderName) setFolderName(d.label || d.name)
  }

  const canStart = !!(activeDrive && selectedProject && folderName && !starting)

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <HardDrive className="text-violet-400" size={20} />
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Archiver</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Festplatten in Projekt-Workspaces spiegeln</p>
        </div>
      </div>

      {/* Drive auswählen */}
      <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Laufwerk</span>
          <button onClick={refresh} disabled={drvLoading}
            className="text-zinc-600 hover:text-zinc-300 transition-colors disabled:opacity-40">
            <RefreshCw size={13} className={drvLoading ? "animate-spin" : ""} />
          </button>
        </div>
        {drives.length > 0 ? (
          <div className="grid gap-2">
            {drives.map(d => (
              <button key={d.mountpoint} onClick={() => handleDriveSelect(d)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-colors ${
                  selectedDrive?.mountpoint === d.mountpoint
                    ? "border-violet-500/50 bg-violet-500/10 text-zinc-100"
                    : "border-white/[6%] hover:border-white/[12%] text-zinc-300"
                }`}>
                <HardDrive size={14} className="text-violet-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{d.label}</div>
                  <div className="text-[11px] text-zinc-500 truncate">{d.mountpoint} · {d.size}</div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-xs text-zinc-600">Kein USB-Laufwerk erkannt.</p>
        )}
        <div>
          <input
            value={customPath}
            onChange={e => { setCustomPath(e.target.value); setSelectedDrive(null) }}
            placeholder="Oder Pfad manuell eingeben: /media/till/..."
            className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-violet-500/50"
          />
        </div>
      </div>

      {/* Ziel */}
      <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4 space-y-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Ziel</span>
        <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)}
          className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-violet-500/50 [&>option]:bg-zinc-900">
          <option value="">Projekt wählen…</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <input
          value={folderName}
          onChange={e => setFolderName(e.target.value)}
          placeholder="Unterordner-Name, z.B. HDD_2010_Blau"
          className="w-full rounded-lg bg-zinc-900 border border-white/[8%] px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500/50"
        />
        <button onClick={handleStart} disabled={!canStart}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors">
          <Play size={13} />
          {starting ? "Starte…" : "Backup starten"}
        </button>
      </div>

      {/* Jobs */}
      {jobs.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Jobs</span>
          {jobs.map(j => (
            <JobCard key={j.id} job={j}
              onCancel={() => archiverApi.cancelJob(j.id).catch(() => {})} />
          ))}
        </div>
      )}
    </div>
  )
}
