import { Activity, Mic, Settings2, Volume2 } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { voiceApi } from "./api"
import type { SettingsResponse, VoiceSettings, VoiceStatus, WakeSensitivity } from "./types"
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
          <div className="grid flex-1 place-items-center p-6 text-center">
            <div className="max-w-sm">
              <Mic size={40} className="mx-auto text-[#2a364b]" />
              <p className="mt-3 text-sm text-[#8d9ab0]">{t("chat_placeholder")}</p>
            </div>
          </div>
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
