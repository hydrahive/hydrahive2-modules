import { useCallback, useEffect, useRef, useState } from "react"
import { ChevronDown, ChevronRight, HardDrive, RefreshCw, Play, Plug, Terminal } from "lucide-react"
import { archiverApi, type Drive, type ArchiveJob } from "./api"
import { JobCard } from "./_JobCard"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface Project { id: string; name: string }

function useDrives() {
  const [drives, setDrives] = useState<Drive[]>([])
  const [loading, setLoading] = useState(false)
  const [mounting, setMounting] = useState<string | null>(null)

  async function refresh() {
    setLoading(true)
    try { setDrives(await archiverApi.drives()) } finally { setLoading(false) }
  }

  async function mountDrive(device: string) {
    setMounting(device)
    try {
      const { mountpoint } = await archiverApi.mountDrive(device)
      setDrives(prev => prev.map(d =>
        d.device === device ? { ...d, mountpoint } : d
      ))
    } catch (e) {
      alert(`Mount fehlgeschlagen: ${e instanceof Error ? e.message : e}`)
    } finally {
      setMounting(null)
      await refresh()
    }
  }

  useEffect(() => { refresh() }, [])
  return { drives, loading, mounting, refresh, mountDrive }
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

function LogPanel() {
  const [open, setOpen] = useState(false)
  const [lines, setLines] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const fetchLog = useCallback(async () => {
    setLoading(true)
    try {
      const { lines: l } = await archiverApi.log(100)
      setLines(l)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!open) return
    fetchLog()
    const t = setInterval(fetchLog, 3000)
    return () => clearInterval(t)
  }, [open, fetchLog])

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [lines, open])

  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[2%] overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 w-full px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <Terminal size={12} />
        Diagnose-Log
        {loading && <RefreshCw size={10} className="animate-spin ml-auto" />}
      </button>
      {open && (
        <div className="border-t border-white/[6%] bg-black/30 px-3 py-2 h-56 overflow-y-auto font-mono text-[10px] leading-relaxed text-zinc-400">
          {lines.length === 0
            ? <span className="text-zinc-600">Keine archiver-Einträge in journald.</span>
            : lines.map((l, i) => <div key={i}>{l}</div>)
          }
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}

export function ArchiverPage() {
  const { drives, loading: drvLoading, mounting, refresh, mountDrive } = useDrives()
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
              <div key={d.device}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-colors ${
                  d.mountpoint
                    ? selectedDrive?.device === d.device
                      ? "border-violet-500/50 bg-violet-500/10 text-zinc-100 cursor-pointer"
                      : "border-white/[6%] hover:border-white/[12%] text-zinc-300 cursor-pointer"
                    : "border-white/[4%] text-zinc-500"
                }`}
                onClick={() => d.mountpoint && handleDriveSelect(d)}
              >
                <HardDrive size={14} className={d.mountpoint ? "text-violet-400" : "text-zinc-600"} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{d.label}</div>
                  <div className="text-[11px] text-zinc-500 truncate">
                    {d.mountpoint || <span className="text-amber-500/80">nicht gemountet</span>}
                    {" · "}{d.size}
                  </div>
                </div>
                {!d.mountpoint && (
                  <button
                    onClick={e => { e.stopPropagation(); mountDrive(d.device) }}
                    disabled={mounting === d.device}
                    className="flex items-center gap-1 px-2 py-1 rounded text-[11px] bg-amber-500/10 border border-amber-500/20 text-amber-300 hover:bg-amber-500/20 disabled:opacity-40 transition-colors flex-shrink-0"
                  >
                    <Plug size={10} />
                    {mounting === d.device ? "…" : "Mounten"}
                  </button>
                )}
              </div>
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

      {/* Log */}
      <LogPanel />
    </div>
  )
}
