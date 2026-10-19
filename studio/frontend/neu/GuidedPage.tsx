/** ATTRAPPE „Geführtes Studio“ (19.10.): nur Oberfläche mit Beispieldaten, nichts wird erzeugt oder gespeichert.
 *  Zweck: Till zeigt sie einem Neuling, bevor gebaut wird. Siehe _work/scratch/studio-neuentwurf.md. */
import { ArrowLeft, ArrowRight, Check, Clapperboard, Film, ImageIcon, Lightbulb, Users } from "lucide-react"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { StepCast } from "./StepCast"
import { StepClips } from "./StepClips"
import { StepFilm } from "./StepFilm"
import { StepIdea } from "./StepIdea"
import { StepImages } from "./StepImages"
import { missing, useGuidedMock, type Guided, type StepId } from "./useGuidedMock"

const STEPS: { n: StepId; title: string; hint: string; Icon: typeof Lightbulb }[] = [
  { n: 1, title: "Idee", hint: "Worum geht es?", Icon: Lightbulb },
  { n: 2, title: "Figuren & Orte", hint: "Wer kommt vor?", Icon: Users },
  { n: 3, title: "Bilder", hint: "Ein Bild je Szene", Icon: ImageIcon },
  { n: 4, title: "Bewegung", hint: "Bilder werden Clips", Icon: Clapperboard },
  { n: 5, title: "Film", hint: "Ansehen & herunterladen", Icon: Film },
]

function Steps({ g }: { g: Guided }) {
  return (
    <nav aria-label="Schritte" className="flex w-64 shrink-0 flex-col gap-1 border-r border-[#1c2433] bg-[#0b111b] p-4">
      <div className="mb-1 text-xs font-black uppercase tracking-[0.2em] text-[#8d9ab0]">Dein Film</div>
      <div className="mb-3 line-clamp-2 text-base font-bold leading-snug text-[#f2f6fc]" title={g.idea}>{g.idea ? g.idea.split(/[.:!?,]/)[0] : "Neuer Film"}</div>
      {STEPS.map(({ n, title, hint, Icon }) => {
        const active = g.step === n
        const done = n < 5 ? missing(g, n) === null : g.film === "done"
        return (
          <button key={n} type="button" onClick={() => g.setStep(n)} aria-current={active ? "step" : undefined}
            className={`flex items-center gap-3 rounded-[10px] px-3 py-3 text-left ${active ? "bg-[#69d7ff]/15 ring-1 ring-[#69d7ff]/60" : "hover:bg-[#1c2940]/60"}`}>
            <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-black ${done ? "bg-[#3ddc97] text-[#04140d]" : active ? "bg-[#69d7ff] text-[#06111c]" : "bg-[#1c2940] text-[#8d9ab0]"}`}>
              {done ? <Check size={18} /> : n}
            </span>
            <span className="min-w-0">
              <span className={`flex items-center gap-1.5 text-base font-bold ${active ? "text-[#f2f6fc]" : "text-[#c3ccdd]"}`}><Icon size={15} /> {title}</span>
              <span className="block text-xs text-[#8d9ab0]">{hint}</span>
            </span>
          </button>
        )
      })}
      <div className="mt-auto space-y-2 border-t border-[#1c2433] pt-3 text-xs text-[#8d9ab0]">
        <p><span className="rounded-full bg-[#1c2940] px-1.5 py-0.5 font-semibold text-[#e8eef8]">≈ 1,5 Cent</span> an einem Knopf heißt: Das kostet ungefähr so viel. Alles andere ist kostenlos.</p>
        <p>Alles, was du hier machst, landet auch in der Profi-Ansicht – dort kannst du genauer schneiden.</p>
        <a href="/studio" className="font-semibold text-[#69d7ff] underline">Zur Profi-Ansicht</a>
      </div>
    </nav>
  )
}

function Footer({ g }: { g: Guided }) {
  const gap = missing(g, g.step)
  const next = STEPS.find((s) => s.n === g.step + 1)
  const prev = STEPS.find((s) => s.n === g.step - 1)
  return (
    <footer className="flex items-center gap-4 border-t border-[#1c2433] bg-[#0b111b] px-8 py-4">
      {prev ? <button type="button" onClick={() => g.setStep(prev.n)} className="flex items-center gap-2 text-sm font-semibold text-[#c3ccdd] hover:text-white"><ArrowLeft size={16} /> Zurück</button> : <span />}
      <span className="ml-auto text-sm text-[#8d9ab0]">{gap}</span>
      {next && (
        <button type="button" onClick={() => g.setStep(next.n)} disabled={g.step === 1 && !g.scenes.length}
          className="flex items-center gap-2 rounded-[10px] bg-[#69d7ff] px-6 py-3 text-base font-black text-[#06111c] hover:bg-[#8fe2ff] disabled:opacity-40">
          Weiter: {next.title} <ArrowRight size={18} />
        </button>
      )}
    </footer>
  )
}

export function GuidedPage() {
  const g = useGuidedMock()
  return (
    <CockpitShell title="Studio" className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/studio" context="Studio · Vorschau" />
      <div className="border-b border-[#ffb86b]/30 bg-[#ffb86b]/10 px-4 py-1.5 text-center text-xs text-[#ffd9ad]" data-guided-mock>
        Vorschau der neuen Bedienung – nur zum Ausprobieren. Hier wird nichts erzeugt, gespeichert oder berechnet.
      </div>
      <div className="flex min-h-0 flex-1 text-[#e8eef8]">
        <Steps g={g} />
        <div className="flex min-w-0 flex-1 flex-col">
          <main className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
            <div className="mx-auto max-w-6xl">
              {g.step === 1 && <StepIdea g={g} />}
              {g.step === 2 && <StepCast g={g} />}
              {g.step === 3 && <StepImages g={g} />}
              {g.step === 4 && <StepClips g={g} />}
              {g.step === 5 && <StepFilm g={g} />}
            </div>
          </main>
          <Footer g={g} />
        </div>
      </div>
    </CockpitShell>
  )
}
