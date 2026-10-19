import type { LibraryItem } from "./api"
import { useElementFromImage } from "./useElementFromImage"
import { useMediaDelete } from "./useMediaDelete"

interface Deps {
  projectId: string
  /** gewähltes Medium (wird nach dem Löschen abgewählt) */
  item: LibraryItem | null
  clearMedia: () => void
  /** alles, was nach dem Löschen neu geladen wird */
  reloadAll: () => void
  /** Baustein in „Planen“ öffnen */
  openElement: (id: string) => void
  notice: (text: string) => void
}

/** Werkzeuge an Dateien (C1, C2): Löschen mit Rückfrage, Figur/Ort aus Bild – Dialoge in einem Stück für StudioPage. */
export function useMediaTools({ projectId, item, clearMedia, reloadAll, openElement, notice }: Deps) {
  const del = useMediaDelete(projectId, (rel) => { if (item?.rel === rel) clearMedia(); reloadAll() }, notice)
  const fromImage = useElementFromImage(projectId, (id) => { clearMedia(); openElement(id) }, notice)
  return {
    ask: del.ask, askItem: del.askItem, createElement: fromImage.ask,
    dialogs: <>{del.dialog}{fromImage.dialog}</>,
  }
}
