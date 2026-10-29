import leerBild from "../assets/leer.webp"

/** Leer-Zustand im Cryptoboard: eigenes Bild des Moduls (Denker-Kopf mit leerer Goldschale) + Hinweistext. */
export function EmptyHint({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-6 text-center">
      <img src={leerBild} alt="" loading="lazy" draggable={false} className="h-20 w-20 select-none object-contain" />
      <p className="text-sm text-zinc-500">{text}</p>
    </div>
  )
}
