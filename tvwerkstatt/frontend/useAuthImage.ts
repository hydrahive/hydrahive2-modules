import { useEffect, useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"

/** Bild über die Schnittstelle laden (mit Anmeldung) und als Blob-Adresse liefern; null solange nichts da ist. */
export function useAuthImage(path: string | null): string | null {
  const [got, setGot] = useState<{ path: string; url: string } | null>(null)
  useEffect(() => {
    if (!path) return
    let alive = true
    let made: string | null = null
    const token = useAuthStore.getState().token
    fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => (r.ok ? r.blob() : null))
      .then((b) => { if (alive && b) { made = URL.createObjectURL(b); setGot({ path, url: made }) } })
      .catch(() => {})
    return () => { alive = false; if (made) URL.revokeObjectURL(made) }
  }, [path])
  return path && got?.path === path ? got.url : null
}
