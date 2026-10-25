import { Bot, Loader2, Save } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { telephonyApi } from "./api"
import { assistantDirty } from "./callsLogic"
import type { AssistantSettings } from "./types"

const input = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500"
const btn = "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"

interface Props {
  saved: AssistantSettings
  busy: boolean
  onSave: (next: AssistantSettings) => Promise<void>
}

/** Modus „Nur Ansage“ / „Telefon-Assistent“ und dessen Einstellungen (Name, Wissen, Modell). */
export function AssistantFields({ saved, busy, onSave }: Props) {
  const { t } = useTranslation("voip")
  const [form, setForm] = useState<AssistantSettings>(saved)
  const [models, setModels] = useState<{ id: string; label?: string }[]>([])
  const [defaultModel, setDefaultModel] = useState("")
  const set = (p: Partial<AssistantSettings>) => setForm((f) => ({ ...f, ...p }))
  const dirty = assistantDirty(form, saved)
  const isAssistant = form.mode === "assistant"

  useEffect(() => {
    if (!isAssistant || models.length) return
    void telephonyApi.models().then((r) => { setModels(r.models); setDefaultModel(r.default) }).catch(() => undefined)
  }, [isAssistant, models.length])

  return (
    <div className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-950/40 p-4" data-voip-assistant="1">
      <div className="flex flex-wrap gap-4 text-sm text-zinc-200" role="radiogroup" aria-label={t("assistant.mode")}>
        {(["greeting", "assistant"] as const).map((m) => (
          <label key={m} className="inline-flex items-center gap-2">
            <input type="radio" name="voip-mode" checked={form.mode === m} onChange={() => set({ mode: m })}
              data-voip-mode={m} />
            {t(`assistant.mode_${m}`)}
          </label>
        ))}
      </div>
      <p className="text-xs leading-5 text-zinc-500">{t(`assistant.mode_${form.mode}_help`)}</p>

      {isAssistant && (
        <>
          <p className="flex items-start gap-2 rounded-lg bg-indigo-500/5 p-3 text-xs leading-5 text-indigo-200">
            <Bot size={15} className="mt-0.5 shrink-0" /> {t("assistant.rights")}
          </p>
          <label className="block space-y-1.5 text-sm text-zinc-300">
            <span>{t("assistant.name")}</span>
            <input className={input} value={form.assistant_name} maxLength={80} placeholder={t("assistant.name_placeholder")}
              onChange={(e) => set({ assistant_name: e.target.value })} data-voip-assistant-name="1" />
            <span className="block text-xs text-zinc-500">{t("assistant.name_help")}</span>
          </label>
          <label className="block space-y-1.5 text-sm text-zinc-300">
            <span>{t("assistant.knowledge")}</span>
            <textarea className={`${input} min-h-32`} value={form.assistant_knowledge} maxLength={4000}
              placeholder={t("assistant.knowledge_placeholder")} data-voip-assistant-knowledge="1"
              onChange={(e) => set({ assistant_knowledge: e.target.value })} />
            <span className="block text-xs text-zinc-500">
              {t("assistant.knowledge_help", { count: form.assistant_knowledge.length })}
            </span>
          </label>
          <label className="block space-y-1.5 text-sm text-zinc-300">
            <span>{t("assistant.model")}</span>
            <select className={input} value={form.assistant_model} onChange={(e) => set({ assistant_model: e.target.value })}
              data-voip-assistant-model="1">
              <option value="">{t("assistant.model_default", { model: defaultModel || "…" })}</option>
              {models.map((m) => <option key={m.id} value={m.id}>{m.label || m.id}</option>)}
            </select>
            <span className="block text-xs text-zinc-500">{t("assistant.model_help")}</span>
          </label>
        </>
      )}

      <button type="button" className={`${btn} bg-zinc-800 text-zinc-100 hover:bg-zinc-700`} disabled={busy || !dirty}
        onClick={() => void onSave(form)} data-voip-assistant-save="1">
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t("assistant.save")}
      </button>
    </div>
  )
}
