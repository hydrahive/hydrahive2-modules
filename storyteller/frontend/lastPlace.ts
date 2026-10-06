// „Weiterschreiben“: zuletzt geöffnete Szene je Projekt. Nur ein Merkzettel im Browser –
// das Buch selbst liegt auf dem Server.
const KEY = (projectId: string) => `storyteller.last.v2.${projectId}`

export interface LastPlace { bookId: string; sceneId: string }

export const lastPlace = {
  get(projectId: string): LastPlace | undefined {
    try {
      const v = JSON.parse(localStorage.getItem(KEY(projectId)) ?? "null") as LastPlace | null
      return v && typeof v.bookId === "string" && typeof v.sceneId === "string" ? v : undefined
    } catch { return undefined }
  },
  set(projectId: string, bookId: string, sceneId: string): void {
    try { localStorage.setItem(KEY(projectId), JSON.stringify({ bookId, sceneId })) } catch { /* Merkzettel ist optional */ }
  },
  clear(projectId: string, bookId: string): void {
    if (this.get(projectId)?.bookId === bookId) {
      try { localStorage.removeItem(KEY(projectId)) } catch { /* egal */ }
    }
  },
}
