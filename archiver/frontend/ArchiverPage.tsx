import { useCallback, useEffect, useRef, useState } from "react"
import { HardDrive, RefreshCw, Terminal, ChevronDown, ChevronRight } from "lucide-react"
import { archiverApi, type Drive, type ArchiveJob } from "./api"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { DriveBox } from "./_DriveBox"
import { DiagnoseBox } from "./_DiagnoseBox"
import { RepairBox } from "./_RepairBox"
import { ArchiveBox } from "./_ArchiveBox"
import { ExportBox } from "./_ExportBox"
import { JobsBox } from "./_JobsBox"

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
      setDrives(prev => prev.map(d => d.device === device ? { ...d, mountpoint } : d))
    } catch (e) {
      alert(`Mount fehlgeschlagen: ${e instanceof Error ? e.message : e}`)
    } finally { setMounting(null); await refresh() }
  }

  async function unmountDrive(device: string, mountpoint: string) {
    setMounting(device)
    try { await archiverApi.unmountDrive(mountpoint) }
    catch (e) { alert(`Unmount fehlgeschlagen: ${e instanceof Error ? e.message : e}`) }
    finally { setMounting(null); await refresh() }
  }

  async function remountDrive(device: string, mountpoint: string) {
    setMounting(device)
    try {
      const { mountpoint: mp } = await archiverApi.remountDrive(device, mountpoint)
      setDrives(prev => prev.map(d => d.device === device ? { ...d, mountpoint: mp } : d))
    } catch (e) {
      alert(`Remount fehlgeschlagen: ${e instanceof Error ? e.message : e}`)
    } finally { setMounting(null); await refresh() }
  }

  useEffect(() => { refresh() }, [])
  return { drives, loading, mounting, refresh, mountDrive, unmountDrive, remountDrive }
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
    try { const { lines: l } = await archiverApi.log(100); setLines(l) }
    finally { setLoading(false) }
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
  const { drives, loading, mounting, refresh, mountDrive, unmountDrive, remountDrive } = useDrives()
  const projects = useProjects()
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)
  const [jobs, setJobs] = useState<ArchiveJob[]>([])

  const selectedDrive = drives.find(d => d.device === selectedDevice) ?? null

  useEffect(() => { archiverApi.jobs().then(setJobs).catch(() => {}) }, [])

  function handleJobStart(job: ArchiveJob) {
    setJobs(prev => [job, ...prev])
    const unsub = archiverApi.streamJob(
      job.id,
      upd => setJobs(prev => prev.map(j => j.id === job.id ? { ...j, ...upd } : j)),
      () => unsub(),
    )
  }

  function handleCancel(id: number) {
    setJobs(prev => prev.map(j => j.id === id ? { ...j, status: "cancelled" } : j))
  }

  function handleSelect(drive: Drive) {
    setSelectedDevice(drive.device)
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center gap-3">
        <HardDrive className="text-violet-400" size={20} />
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Archiver</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Datenträger-Manager</p>
        </div>
      </div>

      <DriveBox
        drives={drives}
        loading={loading}
        mounting={mounting}
        selectedDevice={selectedDevice}
        onSelect={handleSelect}
        onRefresh={refresh}
        onMount={mountDrive}
        onUnmount={unmountDrive}
        onRemount={remountDrive}
      />

      <DiagnoseBox drive={selectedDrive} />

      <RepairBox drive={selectedDrive} />

      <ArchiveBox
        selectedDrive={selectedDrive}
        projects={projects}
        onJobStart={handleJobStart}
      />

      <ExportBox
        drives={drives}
        projects={projects}
        onJobStart={handleJobStart}
      />

      <JobsBox jobs={jobs} onCancel={handleCancel} />

      <LogPanel />
    </div>
  )
}
