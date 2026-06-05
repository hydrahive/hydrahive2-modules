import { useAuthStore } from "@/features/auth/useAuthStore"

const BASE = "/api/modules/archiver"

function headers(): HeadersInit {
  const token = useAuthStore.getState().token ?? ""
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path, { headers: headers() })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: "POST",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export interface Drive {
  name: string
  label: string
  size: string
  mountpoint: string
  transport: string
  device: string
  fstype: string
}

export interface ArchiveJob {
  id: number
  drive_label: string
  project_id: string
  folder_name: string
  target_path: string
  direction: "archive" | "export"
  status: "running" | "done" | "failed" | "cancelled"
  pct: number
  files_done: number
  files_total: number
  speed: string
  error_count: number
  errors: string[]
  started_at?: string
  finished_at?: string
}

export interface WalletFile {
  type: string
  path: string
  size_bytes: number
}

export interface SmartResult {
  health: "PASSED" | "FAILED" | "UNKNOWN"
  raw: string
  available: boolean
}

export interface RepairUpdate {
  lines: string[]
  status: "running" | "done" | "failed" | "not_found"
}

export const archiverApi = {
  drives: () => get<Drive[]>("/drives"),
  mountDrive: (device: string) => post<{ mountpoint: string }>("/drives/mount", { device }),
  unmountDrive: (mountpoint: string) => post<{ ok: boolean }>("/drives/unmount", { mountpoint }),
  remountDrive: (device: string, mountpoint: string) =>
    post<{ mountpoint: string }>("/drives/remount", { device, mountpoint }),

  smart: (deviceName: string) => get<SmartResult>(`/drives/${deviceName}/smart`),
  dmesg: (deviceName: string) => get<{ lines: string[] }>(`/drives/${deviceName}/dmesg`),

  startRepair: (deviceName: string, tool: string) =>
    post<{ ok: boolean }>(`/repair/${deviceName}/start`, { tool }),

  streamRepair(
    deviceName: string,
    onUpdate: (data: RepairUpdate) => void,
    onDone: () => void,
  ): () => void {
    const token = useAuthStore.getState().token ?? ""
    const url = `${BASE}/repair/${deviceName}/stream`
    const es = new EventSource(token ? `${url}?token=${token}` : url)
    es.onmessage = (e) => {
      const data: RepairUpdate = JSON.parse(e.data)
      onUpdate(data)
      if (data.status === "done" || data.status === "failed" || data.status === "not_found") {
        es.close()
        onDone()
      }
    }
    es.onerror = () => { es.close(); onDone() }
    return () => es.close()
  },

  jobs: () => get<ArchiveJob[]>("/jobs"),
  startJob: (body: {
    drive_path: string
    drive_label: string
    project_id: string
    folder_name: string
    direction?: "archive" | "export"
  }) => post<{ id: number; target_path: string }>("/jobs", body),
  cancelJob: (id: number) => post<{ ok: boolean }>(`/jobs/${id}/cancel`),
  scanWallets: (id: number) => get<{ wallets: WalletFile[] }>(`/jobs/${id}/wallets`),

  log: (n = 100) => get<{ lines: string[] }>(`/log?n=${n}`),

  streamJob(id: number, onUpdate: (job: ArchiveJob) => void, onDone: () => void): () => void {
    const token = useAuthStore.getState().token ?? ""
    const url = `${BASE}/jobs/${id}/stream`
    const es = new EventSource(token ? `${url}?token=${token}` : url)
    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.error) { es.close(); onDone(); return }
      onUpdate(data)
      if (["done", "failed", "cancelled"].includes(data.status)) {
        es.close(); onDone()
      }
    }
    es.onerror = () => { es.close(); onDone() }
    return () => es.close()
  },
}
