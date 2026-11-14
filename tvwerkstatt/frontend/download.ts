import { useAuthStore } from "@/features/auth/useAuthStore"

/** Datei über die Schnittstelle (mit Anmeldung) laden und speichern lassen. Name kommt vom Server. */
export async function downloadApk(path: string): Promise<void> {
  const token = useAuthStore.getState().token
  const r = await fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!r.ok) {
    const body = await r.json().catch(() => null)
    throw body ?? { code: "tvw_app_no_build" }
  }
  const name = /filename="([^"]+)"/.exec(r.headers.get("content-disposition") ?? "")?.[1] ?? "hydrahive.apk"
  const url = URL.createObjectURL(await r.blob())
  const a = document.createElement("a")
  a.href = url
  a.download = name
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}
