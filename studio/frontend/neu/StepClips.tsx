/** ATTRAPPE Schritt 4 „Bewegung“: aus dem gewählten Bild wird ein kurzer Clip (hier nur angedeutet). */
import { Clapperboard, Loader2, Pause, RefreshCw, Trash2 } from "lucide-react"
import { COST, ct, motion, MOTION_CSS, type Scene } from "./mockData"
import { BigButton, SmallButton, StepHead } from "./ui"
import type { Guided } from "./useGuidedMock"


function ClipCard({ s, i, g }: { s: Scene; i: number; g: Guided }) {
  const pic = s.images[s.pick]
  const ratio = g.format === "hoch" ? "aspect-[9/16] max-h-[420px]" : "aspect-video"
  return (
    <article className="flex flex-col gap-2 rounded-[12px] border border-[#2a364b] bg-[#0e1420] p-3">
      <div className="flex items-start gap-2">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#1c2940] text-xs font-black text-[#69d7ff]">{i + 1}</span>
        <p className="text-sm leading-snug text-[#e8eef8]">{s.text}</p>
      </div>
      <div className={`relative mx-auto w-full overflow-hidden rounded-[8px] bg-[#080b11] ${ratio}`}>
        {pic ? <img src={pic} alt={`Szene ${i + 1}`} style={s.clip === "done" ? motion : undefined} className="h-full w-full object-cover" />
          : <div className="grid h-full place-items-center p-4 text-center text-sm text-[#8d9ab0]">Noch kein Bild – zurück zu Schritt 3.</div>}
        {s.clip === "busy" && <div className="absolute inset-0 grid place-items-center bg-black/60 text-sm text-white"><span className="flex items-center gap-2"><Loader2 className="animate-spin" size={18} /> Bild wird bewegt … (1–2 Minuten)</span></div>}
        {s.clip === "done" && <span className="absolute left-2 top-2 rounded-full bg-[#3ddc97] px-2 py-0.5 text-xs font-bold text-[#04140d]">✓ bewegt sich · 5 Sek.</span>}
        {s.clip === "still" && <span className="absolute left-2 top-2 rounded-full bg-black/70 px-2 py-0.5 text-xs font-bold text-white">Standbild · 4 Sek.</span>}
      </div>
      {pic && (
        <div className="flex flex-wrap gap-2">
          {(s.clip === "none" || s.clip === "still") && <BigButton onClick={() => void g.makeClip(s.id)} cost={ct(COST.clip)}><Clapperboard size={16} /> Bewegen</BigButton>}
          {s.clip === "none" && <SmallButton onClick={() => g.patchScene(s.id, { clip: "still" })}><Pause size={14} /> Als Standbild lassen</SmallButton>}
          {s.clip === "done" && <>
            <SmallButton onClick={() => void g.makeClip(s.id)}><RefreshCw size={14} /> Neu bewegen ({ct(COST.clip)})</SmallButton>
            <SmallButton onClick={() => g.patchScene(s.id, { clip: "none" })}><Trash2 size={14} /> Bewegung wegwerfen</SmallButton>
          </>}
        </div>
      )}
    </article>
  )
}

export function StepClips({ g }: { g: Guided }) {
  const open = g.scenes.filter((s) => s.images.length && s.clip === "none").length
  return (
    <div>
      <style>{MOTION_CSS}</style>
      <StepHead n={4} title="Bewegung" text={`Jetzt wird aus jedem Bild ein kurzer bewegter Clip (5 Sekunden, ${ct(COST.clip)} je Szene). Du kannst eine Szene auch als Standbild lassen – das ist kostenlos.`} />
      {open > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <BigButton onClick={() => void g.makeAllClips()} cost={ct(open * COST.clip)}><Clapperboard size={16} /> {open === g.scenes.length ? "Alle bewegen" : `Die übrigen ${open} bewegen`}</BigButton>
          <span className="text-sm text-[#8d9ab0]">Läuft weiter, auch wenn du die Seite verlässt.</span>
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {g.scenes.map((s, i) => <ClipCard key={s.id} s={s} i={i} g={g} />)}
      </div>
    </div>
  )
}
