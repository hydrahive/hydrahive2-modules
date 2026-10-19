/** ATTRAPPE Schritt 1 „Idee“: eine Frage, dann Szenen als Karten. */
import { ArrowDown, ArrowUp, Plus, Sparkles, Trash2 } from "lucide-react"
import { EXAMPLE_IDEA, KINDS, LENGTHS } from "./mockData"
import { BigButton, SmallButton, StepHead } from "./ui"
import type { Guided } from "./useGuidedMock"

const pill = (on: boolean) => `rounded-full px-4 py-2 text-sm font-semibold ${on ? "bg-[#69d7ff] text-[#06111c]" : "border border-[#2a364b] text-[#c3ccdd] hover:bg-[#1c2940]"}`

export function StepIdea({ g }: { g: Guided }) {
  return (
    <div>
      <StepHead n={1} title="Idee" text="Erzähl in ein paar Sätzen, worum es in deinem Film gehen soll. Daraus machen wir eine Geschichte in Szenen – die kannst du danach frei ändern." />
      <section className="space-y-4 rounded-[12px] border border-[#2a364b] bg-[#0e1420] p-5">
        <label className="block">
          <span className="text-lg font-bold text-[#f2f6fc]">Worum geht es in deinem Film?</span>
          <textarea value={g.idea} onChange={(e) => g.setIdea(e.target.value)} rows={4} placeholder="Zum Beispiel: Ein Trailer über unseren Hund, der die Welt rettet …"
            className="mt-2 w-full rounded-[8px] border border-[#2a364b] bg-[#080b11] p-3 text-base text-[#e8eef8] outline-none focus:border-[#69d7ff]" />
        </label>
        {!g.idea && <button type="button" onClick={() => g.setIdea(EXAMPLE_IDEA)} className="text-sm text-[#69d7ff] underline">Beispiel einsetzen</button>}
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-28 text-sm text-[#8d9ab0]">Was für ein Film?</span>
          {KINDS.map((k) => <button key={k.id} type="button" className={pill(g.kind === k.id)} onClick={() => g.setKind(k.id)}>{k.label}</button>)}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-28 text-sm text-[#8d9ab0]">Wie lang?</span>
          {LENGTHS.map((l, i) => <button key={l} type="button" className={pill(g.length === i)} onClick={() => g.setLength(i)}>{l}</button>)}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-28 text-sm text-[#8d9ab0]">Wo läuft er?</span>
          <button type="button" className={pill(g.format === "quer")} onClick={() => g.setFormat("quer")}>▭ Bildschirm (quer)</button>
          <button type="button" className={pill(g.format === "hoch")} onClick={() => g.setFormat("hoch")}>▯ Handy (hoch)</button>
        </div>
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <BigButton onClick={() => void g.writeStory()} busy={g.writing} disabled={!g.idea.trim()} cost="≈ 0,2 ct">
            <Sparkles size={16} /> {g.scenes.length ? "Neue Geschichte vorschlagen" : "Geschichte vorschlagen"}
          </BigButton>
          {!g.scenes.length && <BigButton tone="plain" onClick={g.addScene}><Plus size={16} /> Selbst Szenen schreiben</BigButton>}
        </div>
      </section>

      {g.scenes.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-1 text-xl font-black text-[#f2f6fc]">Deine Geschichte · {g.scenes.length} Szenen</h2>
          <p className="mb-3 text-sm text-[#8d9ab0]">Jede Szene wird später ein Bild und dann ein kurzer bewegter Clip. Ändere den Text, wie du magst.</p>
          <ol className="space-y-2">
            {g.scenes.map((s, i) => (
              <li key={s.id} className="flex items-start gap-3 rounded-[10px] border border-[#2a364b] bg-[#0e1420] p-3">
                <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#1c2940] text-sm font-black text-[#69d7ff]">{i + 1}</span>
                <textarea value={s.text} onChange={(e) => g.patchScene(s.id, { text: e.target.value })} rows={2} aria-label={`Szene ${i + 1}`}
                  placeholder="Was passiert in dieser Szene?"
                  className="min-w-0 flex-1 resize-none rounded-[6px] border border-transparent bg-transparent p-1 text-base text-[#e8eef8] outline-none hover:border-[#2a364b] focus:border-[#69d7ff]" />
                <div className="flex shrink-0 gap-1">
                  <SmallButton label="Nach oben" onClick={() => g.moveScene(s.id, -1)} disabled={i === 0}><ArrowUp size={14} /></SmallButton>
                  <SmallButton label="Nach unten" onClick={() => g.moveScene(s.id, 1)} disabled={i === g.scenes.length - 1}><ArrowDown size={14} /></SmallButton>
                  <SmallButton label="Szene löschen" onClick={() => g.removeScene(s.id)}><Trash2 size={14} /></SmallButton>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-3"><SmallButton onClick={g.addScene}><Plus size={14} /> Szene hinzufügen</SmallButton></div>
        </section>
      )}
    </div>
  )
}
