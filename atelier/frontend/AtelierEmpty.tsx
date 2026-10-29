import leerBild from "./assets/leer.webp"

/** Leer-Zustand der großen Atelier-Bereiche (Galerie, Videos, Film, Szenen, Schnitt, Musik):
 *  eigenes Bild des Moduls (Träumer-Kopf mit leerer Leinwand) + Hinweistext.
 *  Kleine Listen (Figuren, Sound-Profile, Auswahl-Dialoge) bleiben bewusst nur Text. */
export function AtelierEmpty({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-6 text-center">
      <img src={leerBild} alt="" loading="lazy" draggable={false} className="h-24 w-24 select-none object-contain" />
      <p className="max-w-sm text-xs text-slate-500">{text}</p>
    </div>
  )
}
