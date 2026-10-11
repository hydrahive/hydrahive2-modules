import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { tonstudioApi } from "./api"
import { errText } from "./errors"
import type { GenerateResult, MusicModel, MusicRequest } from "./types"

interface Props {
  projectId: string
  onDone: () => void
}

const EMPTY: MusicRequest = { style: "", description: "", bpm: null, key: null, duration_s: null, instrumental: false, lyrics: "" }
const input = "rounded bg-slate-900 border border-slate-700 px-2 py-1 text-sm text-slate-200"

/** Clip erzeugen: Modell aus der Adapter-Liste, anbieterneutraler Auftrag (SPEC.md §6). */
export function GenerateDialog({ projectId, onDone }: Props) {
  const { t } = useTranslation("tonstudio")
  const [models, setModels] = useState<MusicModel[]>([])
  const [model, setModel] = useState("")
  const [req, setReq] = useState<MusicRequest>(EMPTY)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [last, setLast] = useState<GenerateResult | null>(null)

  useEffect(() => {
    tonstudioApi.models().then((ms) => {
      setModels(ms)
      setModel((cur) => cur || ms[0]?.id || "")
    }).catch((e) => setError(errText(e)))
  }, [])

  const current = models.find((m) => m.id === model)
  const set = <K extends keyof MusicRequest>(k: K, v: MusicRequest[K]) => setReq((r) => ({ ...r, [k]: v }))
  const num = (v: string) => (v.trim() === "" ? null : Number(v))
  const empty = !req.style.trim() && !req.description.trim() && (req.instrumental || !req.lyrics.trim())

  async function submit() {
    setBusy(true)
    setError("")
    try {
      // Instrumental und Liedtext schließen sich im Backend aus (prompt.py) → Text dann nicht mitschicken.
      setLast(await tonstudioApi.generate(projectId, model, req.instrumental ? { ...req, lyrics: "" } : req))
      onDone()
    } catch (e) {
      setError(errText(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="flex flex-col gap-2 rounded border border-slate-700 bg-slate-800/40 p-3">
      <h3 className="text-sm font-semibold text-slate-200">✨ {t("generate")}</h3>
      <select value={model} onChange={(e) => setModel(e.target.value)} className={input}>
        {models.length === 0 && <option value="">{t("models_none")}</option>}
        {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
      </select>
      {current && (
        <p className="text-[11px] text-slate-500">
          {[current.lyrics && t("cap_lyrics"), current.image_ref && t("cap_image"), current.audio_ref && t("cap_audio"), current.local && t("cap_local")]
            .filter(Boolean).join(" · ")}
          {current.price_note && ` — ${current.price_note}`}
        </p>
      )}
      <input value={req.style} onChange={(e) => set("style", e.target.value)} placeholder={t("style_placeholder")} maxLength={300} className={input} />
      <textarea value={req.description} onChange={(e) => set("description", e.target.value)} placeholder={t("description_placeholder")} maxLength={2000} rows={3} className={input} />
      <div className="grid grid-cols-3 gap-2">
        <input type="number" min={30} max={300} value={req.bpm ?? ""} onChange={(e) => set("bpm", num(e.target.value))} placeholder="BPM" className={input} />
        <input value={req.key ?? ""} onChange={(e) => set("key", e.target.value || null)} placeholder={t("key_placeholder")} maxLength={20} className={input} />
        <input type="number" min={5} max={600} value={req.duration_s ?? ""} onChange={(e) => set("duration_s", num(e.target.value))} placeholder={t("duration_placeholder")} className={input} />
      </div>
      <label className="flex items-center gap-2 text-xs text-slate-300">
        <input type="checkbox" checked={req.instrumental} onChange={(e) => set("instrumental", e.target.checked)} />
        {t("instrumental")}
      </label>
      {!req.instrumental && current?.lyrics && (
        <textarea value={req.lyrics} onChange={(e) => set("lyrics", e.target.value)} placeholder={t("lyrics_placeholder")} maxLength={5000} rows={4} className={input} />
      )}
      <p className="text-[11px] text-slate-500">{t("duration_hint")}</p>
      <button onClick={submit} disabled={busy || !model || empty} className="rounded bg-violet-600 px-3 py-1.5 text-sm text-white disabled:opacity-40">
        {busy ? t("generating") : t("generate_start")}
      </button>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {last && (
        <p className="text-xs text-emerald-400">
          {t("generated_ok", { name: last.name })}
          {last.price_note && <span className="text-slate-500"> — {last.price_note}</span>}
        </p>
      )}
    </section>
  )
}
