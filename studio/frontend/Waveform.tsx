import { slicePeaks } from "./waveLogic"

/** Wellenform im Tonclip: nur der benutzte Ausschnitt (in–out) des Mediums, als Balken über die ganze Clipbreite.
 *  Ohne Werte (noch nicht geladen oder nicht lesbar): flache Linie. Rein darstellend. */
export function Waveform({ peaks, perSecond, from, to }: { peaks?: number[]; perSecond: number; from: number; to: number }) {
  const bars = slicePeaks(peaks, perSecond, from, to)
  if (!bars.length) return <span className="pointer-events-none absolute inset-x-0 top-1/2 h-px bg-white/25" data-waveform="flat" />
  const top = Math.max(...bars, 1)
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-45" viewBox={`0 0 ${bars.length} 100`} preserveAspectRatio="none"
      data-waveform={bars.length} aria-hidden>
      {bars.map((p, i) => {
        const h = Math.max(2, (p / top) * 90)
        return <rect key={i} x={i + 0.1} width={0.8} y={50 - h / 2} height={h} fill="white" />
      })}
    </svg>
  )
}
