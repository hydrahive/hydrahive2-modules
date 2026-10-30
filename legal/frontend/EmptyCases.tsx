import leerBild from "./assets/leer.webp"

/** Leer-Zustand der Fall-Übersicht: eigenes Bild des Moduls (Professor mit Gesetzbuch) + kurzer Text.
 *  Kleine Unterbereiche einer Fallakte (Fristen, Beteiligte, Notizen) bleiben bewusst nur Text. */
export function EmptyCases() {
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center">
      <img src={leerBild} alt="" loading="lazy" draggable={false} className="h-24 w-24 select-none object-contain" />
      <p className="text-sm text-[#9aa7bc]">Noch keine Fälle.</p>
    </div>
  )
}
