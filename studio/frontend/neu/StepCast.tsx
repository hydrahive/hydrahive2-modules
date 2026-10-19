/** ATTRAPPE Schritt 2 „Figuren & Orte“: Foto geben → Probebild ansehen → „Passt“. */
import { Check, ImagePlus, Loader2, MapPin, RefreshCw, Trash2, User, Wand2 } from "lucide-react"
import { ct, type Person } from "./mockData"
import { BigButton, SmallButton, StepHead } from "./ui"
import type { Guided } from "./useGuidedMock"

function PersonCard({ p, g }: { p: Person; g: Guided }) {
  const Icon = p.kind === "figur" ? User : MapPin
  return (
    <article className={`flex flex-col gap-3 rounded-[12px] border p-4 ${p.state === "passt" ? "border-[#3ddc97]/60 bg-[#3ddc97]/5" : "border-[#2a364b] bg-[#0e1420]"}`}>
      <div className="flex items-center gap-2">
        <Icon size={18} className="text-[#69d7ff]" />
        <input value={p.name} onChange={(e) => g.patchPerson(p.id, { name: e.target.value })} placeholder={p.kind === "figur" ? "Name der Figur" : "Name des Ortes"}
          aria-label="Name" className="min-w-0 flex-1 rounded-[6px] border border-[#2a364b] bg-[#080b11] px-2 py-1.5 text-base font-bold text-[#f2f6fc] outline-none focus:border-[#69d7ff]" />
        <SmallButton label={`${p.name || "Eintrag"} löschen`} onClick={() => g.removePerson(p.id)}><Trash2 size={14} /></SmallButton>
      </div>

      {p.state === "leer" && (
        <div className="grid gap-2">
          <button type="button" onClick={() => void g.givePhoto(p.id)}
            className="flex flex-col items-center gap-2 rounded-[10px] border-2 border-dashed border-[#46617f] p-6 text-center text-sm text-[#c3ccdd] hover:border-[#69d7ff] hover:bg-[#69d7ff]/5">
            <ImagePlus size={28} className="text-[#69d7ff]" />
            <span className="font-bold">Foto hineinziehen oder hier klicken</span>
            <span className="text-xs text-[#8d9ab0]">Ein deutliches Foto reicht. Die KI macht daraus ein Probebild.</span>
          </button>
          <BigButton tone="plain" onClick={() => g.patchPerson(p.id, { state: "ohne" })}><Wand2 size={16} /> Kein Foto – die KI erfindet {p.kind === "figur" ? "die Figur" : "den Ort"}</BigButton>
        </div>
      )}

      {p.state === "busy" && (
        <div className="flex items-center gap-3 rounded-[10px] bg-[#080b11] p-6 text-sm text-[#c3ccdd]">
          <Loader2 size={20} className="animate-spin text-[#69d7ff]" /> Die KI zeichnet ein Probebild …
        </div>
      )}

      {(p.state === "probe" || p.state === "passt") && p.probe && (
        <div className="space-y-2">
          <div className="grid grid-cols-[1fr_2fr] gap-2">
            <figure><img src={p.photo} alt="Dein Foto" className="aspect-square w-full rounded-[8px] object-cover" /><figcaption className="mt-1 text-center text-xs text-[#8d9ab0]">Dein Foto</figcaption></figure>
            <figure><img src={p.probe} alt="Probebild" className="aspect-video w-full rounded-[8px] object-cover" /><figcaption className="mt-1 text-center text-xs text-[#8d9ab0]">So sieht {p.name || "sie"} im Film aus</figcaption></figure>
          </div>
          {p.state === "probe" ? (
            <div className="flex flex-wrap gap-2">
              <BigButton onClick={() => g.patchPerson(p.id, { state: "passt" })}><Check size={16} /> Passt</BigButton>
              <BigButton tone="plain" onClick={() => void g.retryProbe(p.id, p.probe)} cost={ct(1.5)}><RefreshCw size={16} /> Anderes Probebild</BigButton>
              <BigButton tone="plain" onClick={() => g.patchPerson(p.id, { state: "leer", photo: undefined, probe: undefined })}>Anderes Foto</BigButton>
            </div>
          ) : (
            <div className="flex items-center justify-between text-sm font-bold text-[#3ddc97]">
              <span className="flex items-center gap-1"><Check size={16} /> Fertig – {p.name || "sie"} sieht in jeder Szene so aus.</span>
              <SmallButton onClick={() => g.patchPerson(p.id, { state: "probe" })}>Ändern</SmallButton>
            </div>
          )}
        </div>
      )}

      {p.state === "ohne" && (
        <div className="flex items-center justify-between rounded-[10px] bg-[#080b11] p-3 text-sm text-[#c3ccdd]">
          <span>Die KI erfindet {p.kind === "figur" ? "die Figur" : "den Ort"} nach deiner Geschichte.</span>
          <SmallButton onClick={() => g.patchPerson(p.id, { state: "leer" })}>Doch ein Foto</SmallButton>
        </div>
      )}
    </article>
  )
}

export function StepCast({ g }: { g: Guided }) {
  const names = g.people.filter((p) => p.name).map((p) => p.name)
  return (
    <div>
      <StepHead n={2} title="Figuren & Orte" text="Wer und was soll in jeder Szene gleich aussehen? Gib ein Foto – du siehst sofort, wie es im Film aussehen wird." />
      {names.length > 0 && (
        <p className="mb-4 rounded-[10px] border border-[#69d7ff]/30 bg-[#69d7ff]/5 p-3 text-sm text-[#cdeeff]">
          In deiner Geschichte kommen vor: <b>{names.join(", ")}</b>. Gib ihnen ein Foto, dann sehen sie überall gleich aus.
        </p>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {g.people.map((p) => <PersonCard key={p.id} p={p} g={g} />)}
        <div className="flex flex-col justify-center gap-2 rounded-[12px] border border-dashed border-[#2a364b] p-4">
          <BigButton tone="plain" onClick={() => g.addPerson("figur")}><User size={16} /> Figur hinzufügen</BigButton>
          <BigButton tone="plain" onClick={() => g.addPerson("ort")}><MapPin size={16} /> Ort hinzufügen</BigButton>
          <p className="text-xs text-[#8d9ab0]">Figur = Mensch, Tier, Maskottchen. Ort = ein Platz, der öfter vorkommt.</p>
        </div>
      </div>
    </div>
  )
}
