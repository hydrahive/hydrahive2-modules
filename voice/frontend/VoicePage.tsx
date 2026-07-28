import { Activity, Cpu, Mic, Send, Settings2, Volume2 } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { voiceApi } from "./api"
import type {
  LlmModel, LlmState, SettingsResponse, TranscriptTurn, VoiceSettings,
  VoiceStatus, WakeSensitivity,
} from "./types"
import { WAKE_SENSITIVITIES } from "./types"

/**
 * Voicebox — Etappe 2.
 *
 * Links: Geräte-Einstellungen (Lautstärke, Mute, Wake-Sound, Wake-Word-
 * Empfindlichkeit, LED-Ring) — live gelesen und gesetzt über die Bridge.
 * Rechts: echter Bridge-/Geräte-Status. Mitte: Chat-Platzhalter (E4).
 */
export function VoicePage() {
  const { t } = useTranslation("voice")
  const [status, setStatus] = useState<VoiceStatus | null>(null)
  const [settings, setSettings] = useState<VoiceSettings | null>(null)
  const [bridgeDown, setBridgeDown] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await voiceApi.status())
    } catch {
      setStatus({ module: "voice", stage: "e2", bridge: "down", device: "disconnected" })
    }
  }, [])

  const loadSettings = useCallback(async () => {
    try {
      const res: SettingsResponse = await voiceApi.getSettings()
      setBridgeDown(res.bridge === "down")
      setSettings(res.settings)
    } catch {
      setBridgeDown(true)
      setSettings(null)
    }
  }, [])

  useEffect(() => {
    let alive = true
    const tick = async () => {
      await Promise.all([loadStatus(), loadSettings()])
      if (alive) setLoading(false)
    }
    tick()
    const iv = setInterval(loadStatus, 5000)
    return () => {
      alive = false
      clearInterval(iv)
    }
  }, [loadStatus, loadSettings])

  // ── LLM-Auswahl (E5) ─────────────────────────────────────────────────────
  const [llm, setLlm] = useState<LlmState | null>(null)
  const [llmModels, setLlmModels] = useState<LlmModel[]>([])
  const [llmSaving, setLlmSaving] = useState(false)

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const [state, models] = await Promise.all([
          voiceApi.getLlm(),
          voiceApi.llmModels(),
        ])
        if (!alive) return
        setLlm(state)
        setLlmModels(models.models)
      } catch {
        if (alive) setLlm(null)
      }
    }
    load()
    return () => {
      alive = false
    }
  }, [])

  const setLlmModel = useCallback(async (model: string | null) => {
    setLlmSaving(true)
    try {
      const next = await voiceApi.putLlm(model)
      setLlm(next)
    } catch {
      // Zustand neu laden bei Fehler
      try {
        setLlm(await voiceApi.getLlm())
      } catch { /* ignore */ }
    } finally {
      setLlmSaving(false)
    }
  }, [])

  // ── Voice-Verlauf (E3): inkrementelles Polling per Cursor ────────────────
  const [turns, setTurns] = useState<TranscriptTurn[]>([])
  const cursorRef = useRef(0)
  const optimisticIdRef = useRef(-1)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const poll = async () => {
      try {
        const res = await voiceApi.transcript(cursorRef.current, 50)
        if (!alive) return
        if (res.turns.length > 0) {
          cursorRef.current = res.cursor
          setTurns((prev) => {
            // Optimistische Bubbles (negative id) entfernen, deren Text jetzt
            // als echter user-Turn ankommt — verhindert Doppelanzeige.
            const incomingUserTexts = new Set(
              res.turns.filter((x) => x.role === "user").map((x) => x.text),
            )
            const cleaned = prev.filter(
              (x) => !(x.id < 0 && incomingUserTexts.has(x.text)),
            )
            return [...cleaned, ...res.turns].slice(-200)
          })
        }
      } catch {
        /* still, Status-Panel zeigt bridge down */
      }
    }
    poll()
    const iv = setInterval(poll, 3000)
    return () => {
      alive = false
      clearInterval(iv)
    }
  }, [])

  const sendText = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || sending) return
    setSending(true)
    setSendError(null)
    // Optimistischer User-Bubble mit negativer id (kollidiert nicht mit echten).
    const optimistic: TranscriptTurn = {
      id: optimisticIdRef.current--,
      ts: Date.now() / 1000,
      role: "user",
      kind: "speech",
      text: trimmed,
    }
    setTurns((prev) => [...prev, optimistic].slice(-200))
    try {
      await voiceApi.say(trimmed)
      // Der echte Turn (inkl. Antwort) kommt über das nächste Poll.
    } catch {
      setSendError(t("send_error"))
      // optimistischen Bubble wieder entfernen
      setTurns((prev) => prev.filter((x) => x.id !== optimistic.id))
    } finally {
      setSending(false)
    }
  }, [sending, t])

  const patch = useCallback(async (p: Partial<VoiceSettings>) => {
    setSaving(true)
    setError(null)
    // Optimistisch anwenden
    setSettings((s) => (s ? { ...s, ...p } : s))
    try {
      const res = await voiceApi.putSettings(p)
      if (res.settings) setSettings(res.settings)
      setBridgeDown(res.bridge === "down")
    } catch {
      setError(t("save_error"))
      await loadSettings() // echten Stand zurückholen
    } finally {
      setSaving(false)
    }
  }, [t, loadSettings])

  return (
    <CockpitShell
      title="Voice"
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="/voice" context={t("subtitle")} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[300px_minmax(520px,1fr)_330px]">
        {/* Links: Einstellungen */}
        <aside className="hidden min-h-0 overflow-y-auto xl:block">
          <Panel icon={<Settings2 size={14} />} title={t("settings_title")}>
            {loading ? (
              <p className="text-xs text-[#8d9ab0]">{t("loading")}</p>
            ) : bridgeDown || !settings ? (
              <p className="text-xs leading-4 text-[#e0a04a]">{t("bridge_down")}</p>
            ) : (
              <SettingsForm
                s={settings}
                saving={saving}
                error={error}
                onPatch={patch}
                t={t}
              />
            )}
          </Panel>

          <div className="mt-[10px]">
            <Panel icon={<Cpu size={14} />} title={t("llm_title")}>
              <LlmPicker
                llm={llm}
                models={llmModels}
                saving={llmSaving}
                onChange={setLlmModel}
                t={t}
              />
            </Panel>
          </div>
        </aside>

        {/* Mitte: Voice-Agent-Chat (E4) */}
        <main className="flex min-h-0 flex-col overflow-hidden rounded-[6px] border border-[#1c2636] bg-[#0a0f18]">
          <header className="flex items-center gap-2 border-b border-[#1c2636] px-4 py-3">
            <span className="grid h-8 w-8 place-items-center rounded-[4px] bg-[radial-gradient(circle_at_50%_20%,rgba(105,215,255,.3),rgba(8,11,17,.9))]">
              <Mic size={16} className="text-[#69d7ff]" />
            </span>
            <div>
              <div className="text-sm font-bold text-[#e8eef8]">{t("title")}</div>
              <div className="text-xs text-[#8d9ab0]">{t("subtitle")}</div>
            </div>
          </header>
          <TranscriptView turns={turns} t={t} />
          <Composer
            disabled={bridgeDown}
            sending={sending}
            error={sendError}
            onSend={sendText}
            t={t}
          />
        </main>

        {/* Rechts: Status */}
        <aside className="hidden min-h-0 overflow-y-auto xl:block">
          <Panel icon={<Activity size={14} />} title={t("status_title")}>
            <StatusRows status={status} t={t} />
          </Panel>
        </aside>
      </div>
    </CockpitShell>
  )
}

function TranscriptView({
  turns,
  t,
}: {
  turns: TranscriptTurn[]
  t: (k: string) => string
}) {
  const endRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [turns.length])

  if (turns.length === 0) {
    return (
      <div className="grid flex-1 place-items-center p-6 text-center">
        <div className="max-w-sm">
          <Mic size={40} className="mx-auto text-[#2a364b]" />
          <p className="mt-3 text-sm text-[#8d9ab0]">{t("empty_hint")}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 space-y-2 overflow-y-auto p-4">
      {turns.map((turn) => (
        <Bubble key={turn.id} turn={turn} t={t} />
      ))}
      <div ref={endRef} />
    </div>
  )
}

function Composer({
  disabled,
  sending,
  error,
  onSend,
  t,
}: {
  disabled: boolean
  sending: boolean
  error: string | null
  onSend: (text: string) => void
  t: (k: string) => string
}) {
  const [text, setText] = useState("")
  const submit = () => {
    if (!text.trim() || sending || disabled) return
    onSend(text)
    setText("")
  }
  return (
    <div className="border-t border-[#1c2636] p-3">
      {error && <p className="mb-1.5 text-xs text-[#e0a0a0]">{error}</p>}
      <div className="flex items-end gap-2">
        <textarea
          value={text}
          disabled={disabled}
          rows={1}
          placeholder={t("input_placeholder")}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          className="max-h-32 min-h-[38px] flex-1 resize-none rounded-[6px] border border-[#1c2636] bg-[#0b1119] px-3 py-2 text-sm text-[#e8eef8] outline-none placeholder:text-[#5a6880] focus:border-[#3a6ea5] disabled:opacity-50"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || sending || !text.trim()}
          className="grid h-[38px] w-[38px] shrink-0 place-items-center rounded-[6px] bg-[#1f5f8b] text-white transition-colors hover:bg-[#2670a3] disabled:opacity-40"
          aria-label={t("send")}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}

function Bubble({ turn, t }: { turn: TranscriptTurn; t: (k: string) => string }) {
  const isUser = turn.role === "user"
  const isError = turn.kind === "error"
  const time = new Date(turn.ts * 1000).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  })
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-[8px] px-3 py-2 text-sm ${
          isUser
            ? "bg-[#173247] text-[#e8eef8]"
            : isError
              ? "border border-[#5a2a2a] bg-[#1f1113] text-[#e0a0a0]"
              : "border border-[#1c2636] bg-[#0e1420] text-[#d6e0ee]"
        }`}
      >
        <div className="mb-0.5 flex items-center gap-2 text-[10px] uppercase tracking-wide text-[#6b7a92]">
          <span>{isUser ? t("you") : t("assistant")}</span>
          {turn.kind === "media" && <span className="text-[#69d7ff]">♪ {t("kind_media")}</span>}
          <span className="ml-auto tabular-nums">{time}</span>
        </div>
        <div className="whitespace-pre-wrap leading-snug">{turn.text}</div>
      </div>
    </div>
  )
}

function StatusRows({
  status,
  t,
}: {
  status: VoiceStatus | null
  t: (k: string) => string
}) {
  const bridgeUp = status?.bridge === "up"
  const deviceOn = status?.device === "connected"
  return (
    <div className="space-y-2 text-xs">
      <StatusRow label={t("st_bridge")} ok={bridgeUp} onText={t("st_up")} offText={t("st_down")} />
      <StatusRow
        label={t("st_device")}
        ok={deviceOn}
        onText={t("st_connected")}
        offText={t("st_disconnected")}
      />
    </div>
  )
}

function StatusRow({
  label,
  ok,
  onText,
  offText,
}: {
  label: string
  ok: boolean
  onText: string
  offText: string
}) {
  return (
    <div className="flex items-center justify-between rounded-[4px] border border-[#1c2636] bg-[#0b1119] px-2.5 py-2">
      <span className="text-[#8d9ab0]">{label}</span>
      <span className="flex items-center gap-1.5 font-semibold">
        <span
          className={`h-2 w-2 rounded-full ${ok ? "bg-[#4ade80]" : "bg-[#e05a5a]"}`}
        />
        <span className={ok ? "text-[#cfe6d6]" : "text-[#e0a0a0]"}>
          {ok ? onText : offText}
        </span>
      </span>
    </div>
  )
}

function LlmPicker({
  llm,
  models,
  saving,
  onChange,
  t,
}: {
  llm: LlmState | null
  models: LlmModel[]
  saving: boolean
  onChange: (model: string | null) => void
  t: (k: string) => string
}) {
  if (!llm) {
    return <p className="text-xs text-[#8d9ab0]">{t("loading")}</p>
  }
  const defaultLabel =
    models.find((m) => m.id === llm.agent_default)?.label || llm.agent_default || "—"
  return (
    <div className="space-y-2">
      <select
        value={llm.override || ""}
        disabled={saving || !llm.has_session}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full rounded-[4px] border border-[#1c2636] bg-[#0b1119] px-2 py-1.5 text-xs text-[#e8eef8] outline-none focus:border-[#3a6ea5] disabled:opacity-50"
      >
        <option value="">{t("llm_agent_default")} ({defaultLabel})</option>
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label}
          </option>
        ))}
      </select>
      {!llm.has_session ? (
        <p className="text-[11px] leading-4 text-[#8d9ab0]">{t("llm_no_session")}</p>
      ) : llm.override ? (
        <p className="text-[11px] leading-4 text-[#69d7ff]">{t("llm_override_active")}</p>
      ) : (
        <p className="text-[11px] leading-4 text-[#8d9ab0]">{t("llm_using_default")}</p>
      )}
    </div>
  )
}

function SettingsForm({
  s,
  saving,
  error,
  onPatch,
  t,
}: {
  s: VoiceSettings
  saving: boolean
  error: string | null
  onPatch: (p: Partial<VoiceSettings>) => void
  t: (k: string) => string
}) {
  return (
    <div className="space-y-3.5">
      {/* Lautstärke */}
      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-[#8d9ab0]">
          <span className="flex items-center gap-1.5">
            <Volume2 size={12} /> {t("volume")}
          </span>
          <span className="tabular-nums text-[#cfe0f0]">
            {Math.round(s.volume * 100)}%
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={Math.round(s.volume * 100)}
          disabled={saving}
          onChange={(e) => onPatch({ volume: Number(e.target.value) / 100 })}
          className="w-full accent-[#69d7ff]"
        />
      </div>

      {/* Toggles */}
      <Toggle
        label={t("mute")}
        checked={s.mute}
        disabled={saving}
        onChange={(v) => onPatch({ mute: v })}
      />
      <Toggle
        label={t("wake_sound")}
        checked={s.wake_sound}
        disabled={saving}
        onChange={(v) => onPatch({ wake_sound: v })}
      />

      {/* Wake-Word-Empfindlichkeit */}
      <div>
        <label className="mb-1 block text-xs text-[#8d9ab0]">{t("sensitivity")}</label>
        <select
          value={s.wake_word_sensitivity || ""}
          disabled={saving}
          onChange={(e) =>
            onPatch({ wake_word_sensitivity: e.target.value as WakeSensitivity })
          }
          className="w-full rounded-[4px] border border-[#1c2636] bg-[#0b1119] px-2 py-1.5 text-xs text-[#e8eef8] outline-none focus:border-[#3a6ea5]"
        >
          {WAKE_SENSITIVITIES.map((opt) => (
            <option key={opt} value={opt}>
              {t(`sens_${opt.split(" ")[0].toLowerCase()}`)}
            </option>
          ))}
        </select>
      </div>

      {/* LED-Ring */}
      <Toggle
        label={t("led_on")}
        checked={s.led_on}
        disabled={saving}
        onChange={(v) => onPatch({ led_on: v })}
      />
      {s.led_on && (
        <div>
          <div className="mb-1 flex items-center justify-between text-xs text-[#8d9ab0]">
            <span>{t("led_brightness")}</span>
            <span className="tabular-nums text-[#cfe0f0]">
              {Math.round(s.led_brightness * 100)}%
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={Math.round(s.led_brightness * 100)}
            disabled={saving}
            onChange={(e) => onPatch({ led_brightness: Number(e.target.value) / 100 })}
            className="w-full accent-[#69d7ff]"
          />
        </div>
      )}

      {error && <p className="text-xs text-[#e0a0a0]">{error}</p>}
    </div>
  )
}

function Toggle({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string
  checked: boolean
  disabled?: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between text-xs text-[#c7d3e5]">
      <span>{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition-colors ${
          checked ? "bg-[#3a8ec5]" : "bg-[#26303f]"
        } ${disabled ? "opacity-50" : ""}`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </button>
    </label>
  )
}

function Panel({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-[6px] border border-[#1c2636] bg-[#0a0f18] p-3">
      <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[#69d7ff]">
        {icon}
        {title}
      </div>
      {children}
    </section>
  )
}
