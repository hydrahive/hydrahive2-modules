/** ATTRAPPE Schritt 5 „Film“: ganzer Film am Stück, Musik/Stimme/Untertitel als Schalter, erzeugen, herunterladen. */
import { useEffect, useState } from "react"
import { Download, Film, Pause, Play } from "lucide-react"
import { COST, ct, motion, MOTION_CSS } from "./mockData"
import { BigButton, Notice, StepHead } from "./ui"
import type { Guided } from "./useGuidedMock"

function Toggle({ on, label, hint, onChange }: { on: boolean; label: string; hint: string; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-[10px] border border-[#2a364b] p-3 hover:bg-[#1c2940]/40">
      <input type="checkbox" checked={on} onChange={(e) => onChange(e.target.checked)} className="mt-1 h-5 w-5 accent-[#3ddc97]" />
      <span><span className="block text-base font-bold text-[#f2f6fc]">{label}</span><span className="text-sm text-[#8d9ab0]">{hint}</span></span>
    </label>
  )
}

export function StepFilm({ g }: { g: Guided }) {
  const shown = g.scenes.filter((s) => s.images.length)
  const [at, setAt] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [note, setNote] = useState(false)
  useEffect(() => {
    if (!playing || !shown.length) return
    const t = setInterval(() => setAt((a) => (a + 1) % shown.length), 2500)
    return () => clearInterval(t)
  }, [playing, shown.length])
  const cur = shown[at % Math.max(1, shown.length)]
  const extra = (g.extras.music ? COST.music : 0) + (g.extras.voice ? COST.voice * g.scenes.length : 0)
  return (
    <div>
      <style>{MOTION_CSS}</style>
      <StepHead n={5} title="Film" text="Hier siehst du deinen ganzen Film. Wähl Musik und Untertitel dazu – dann wird er zu einer Datei, die du herunterladen kannst." />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <section>
          <div className={`relative mx-auto overflow-hidden rounded-[12px] bg-black ${g.format === "hoch" ? "aspect-[9/16] max-h-[560px]" : "aspect-video"}`}>
            {cur ? <img key={cur.id} src={cur.images[cur.pick]} alt="Film" style={cur.clip === "done" ? motion : undefined} className="h-full w-full object-cover" />
              : <div className="grid h-full place-items-center text-[#8d9ab0]">Noch keine Bilder – zurück zu Schritt 3.</div>}
            {cur && g.extras.subtitles && <div className="absolute inset-x-6 bottom-5 rounded bg-black/70 px-3 py-1.5 text-center text-base text-white">{cur.text}</div>}
          </div>
          {shown.length > 0 && (
            <div className="mt-3 flex items-center gap-3">
              <button type="button" onClick={() => setPlaying(!playing)}
                className="flex h-12 shrink-0 items-center gap-2 rounded-full bg-[#69d7ff] px-5 text-base font-bold text-[#06111c]">{playing ? <><Pause size={20} /> Anhalten</> : <><Play size={20} /> Abspielen</>}</button>
              <div className="flex flex-1 gap-1">
                {shown.map((s, i) => (
                  <button key={s.id} type="button" onClick={() => setAt(i)} aria-label={`Szene ${g.scenes.indexOf(s) + 1}`}
                    className={`h-12 flex-1 overflow-hidden rounded-[4px] border-2 ${i === at % shown.length ? "border-[#69d7ff]" : "border-transparent opacity-60"}`}>
                    <img src={s.images[s.pick]} alt="" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>
        <section className="space-y-3">
          <Toggle on={g.extras.music} label="Musik" hint={`Die KI macht passende Musik zum Film (${ct(COST.music)}).`} onChange={(v) => g.setExtras({ ...g.extras, music: v })} />
          <Toggle on={g.extras.voice} label="Erzählstimme" hint="Eine Stimme liest die Szenen-Texte vor." onChange={(v) => g.setExtras({ ...g.extras, voice: v })} />
          <Toggle on={g.extras.subtitles} label="Untertitel" hint="Zum Ein- und Ausschalten im Abspieler – nicht ins Bild gebrannt." onChange={(v) => g.setExtras({ ...g.extras, subtitles: v })} />
          <div className="pt-2">
            {g.film !== "done"
              ? <BigButton onClick={() => void g.makeFilm()} busy={g.film === "busy"} disabled={!shown.length} cost={extra ? ct(extra) : undefined}><Film size={16} /> {g.film === "busy" ? "Film entsteht …" : "Film erzeugen"}</BigButton>
              : <div className="space-y-2">
                  <BigButton onClick={() => setNote(true)}><Download size={16} /> Film herunterladen</BigButton>
                  <p className="text-sm text-[#3ddc97]">Fertig! Dein Film liegt auch in „Meine Filme“.</p>
                </div>}
          </div>
          {note && <Notice>Das ist nur eine Vorschau der Bedienung – hier wird noch nichts heruntergeladen.</Notice>}
        </section>
      </div>
    </div>
  )
}
