/** ATTRAPPE Schritt 3 „Bilder“: je Szene ein Bild, blättern, neu, verwerfen. */
import { ChevronLeft, ChevronRight, ImageIcon, Loader2, RefreshCw, Sparkles, Trash2 } from "lucide-react"
import { COST, ct, type Scene } from "./mockData"
import { BigButton, CastChips, SmallButton, StepHead } from "./ui"
import type { Guided } from "./useGuidedMock"

function ImageCard({ s, i, g }: { s: Scene; i: number; g: Guided }) {
  const toggle = (id: string) => g.patchScene(s.id, (x) => ({ cast: x.cast.includes(id) ? x.cast.filter((c) => c !== id) : [...x.cast, id] }))
  const ratio = g.format === "hoch" ? "aspect-[9/16] max-h-[420px]" : "aspect-video"
  return (
    <article className="flex flex-col gap-2 rounded-[12px] border border-[#2a364b] bg-[#0e1420] p-3">
      <div className="flex items-start gap-2">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#1c2940] text-xs font-black text-[#69d7ff]">{i + 1}</span>
        <p className="text-sm leading-snug text-[#e8eef8]">{s.text || <i className="text-[#8d9ab0]">Szene ohne Text</i>}</p>
      </div>
      <div className={`relative mx-auto w-full overflow-hidden rounded-[8px] bg-[#080b11] ${ratio}`}>
        {s.images.length > 0 && <img src={s.images[s.pick]} alt={`Bild zu Szene ${i + 1}`} className="h-full w-full object-cover" />}
        {s.images.length === 0 && !s.imageBusy && (
          <div className="grid h-full place-items-center text-center text-sm text-[#8d9ab0]"><span><ImageIcon className="mx-auto mb-1" size={26} />Noch kein Bild</span></div>
        )}
        {s.imageBusy && (
          <div className="absolute inset-0 grid place-items-center bg-black/60 text-sm text-[#e8eef8]"><span className="flex items-center gap-2"><Loader2 className="animate-spin" size={18} /> Bild entsteht …</span></div>
        )}
        {s.images.length > 1 && (
          <>
            <button type="button" aria-label="Vorheriges Bild" onClick={() => g.flip(s.id, -1)} className="absolute left-1 top-1/2 -translate-y-1/2 rounded-full bg-black/60 p-1.5 text-white"><ChevronLeft size={18} /></button>
            <button type="button" aria-label="Nächstes Bild" onClick={() => g.flip(s.id, 1)} className="absolute right-1 top-1/2 -translate-y-1/2 rounded-full bg-black/60 p-1.5 text-white"><ChevronRight size={18} /></button>
            <span className="absolute bottom-1 right-2 rounded-full bg-black/70 px-2 py-0.5 text-xs text-white">Bild {s.pick + 1} von {s.images.length}</span>
          </>
        )}
      </div>
      <CastChips people={g.people} cast={s.cast} onToggle={toggle} />
      <div className="flex flex-wrap gap-2">
        {s.images.length === 0
          ? <BigButton onClick={() => void g.makeImage(s.id)} busy={s.imageBusy} cost={ct(COST.image)}><Sparkles size={16} /> Bild machen</BigButton>
          : <>
              <SmallButton onClick={() => void g.makeImage(s.id)} disabled={s.imageBusy}><RefreshCw size={14} /> Noch eins ({ct(COST.image)})</SmallButton>
              <SmallButton onClick={() => g.dropImage(s.id)}><Trash2 size={14} /> Dieses Bild wegwerfen</SmallButton>
            </>}
      </div>
    </article>
  )
}

export function StepImages({ g }: { g: Guided }) {
  const open = g.scenes.filter((s) => !s.images.length && !s.imageBusy).length
  return (
    <div>
      <StepHead n={3} title="Bilder" text="Für jede Szene entsteht ein Bild. Gefällt es nicht, mach noch eins – mit den Pfeilen blätterst du, das gezeigte Bild kommt in den Film." />
      {g.scenes.length === 0 ? (
        <p className="rounded-[10px] border border-[#2a364b] p-6 text-base text-[#c3ccdd]">Noch keine Szenen. Geh zurück zu <b>Schritt 1 · Idee</b>.</p>
      ) : (
        <>
          {open > 0 && (
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <BigButton onClick={() => void g.makeAllImages()} cost={ct(open * COST.image)}><Sparkles size={16} /> {open === g.scenes.length ? "Alle Bilder machen" : `Die fehlenden ${open} Bilder machen`}</BigButton>
              <span className="text-sm text-[#8d9ab0]">Dauert etwa eine halbe Minute je Bild.</span>
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
            {g.scenes.map((s, i) => <ImageCard key={s.id} s={s} i={i} g={g} />)}
          </div>
        </>
      )}
    </div>
  )
}
