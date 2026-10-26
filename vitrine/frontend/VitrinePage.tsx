import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Save } from "lucide-react"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { vitrineApi, type VideoFile, type VitrineConfig } from "./api"
import { ruleErrors, type Template } from "./rules"
import { StatusCard } from "./StatusCard"
import { VideoList } from "./VideoList"
import { RuleList } from "./RuleList"
import { DashboardCard } from "./DashboardCard"
import { SettingsCard } from "./SettingsCard"
import { MessagesCard } from "./MessagesCard"
import { BluetoothCard } from "./BluetoothCard"
import { LightCard } from "./LightCard"
import { lightErrors, normalizeLight } from "./light"

export function VitrinePage() {
  const { t } = useTranslation("vitrine")
  const [config, setConfig] = useState<VitrineConfig | null>(null)
  const [saved, setSaved] = useState<string>("")
  const [videos, setVideos] = useState<VideoFile[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [loadErr, setLoadErr] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [saving, setSaving] = useState(false)

  const loadVideos = useCallback(() => { vitrineApi.videos().then(setVideos).catch(() => {}) }, [])
  useEffect(() => {
    Promise.all([vitrineApi.config(), vitrineApi.templates()])
      .then(([c, tpl]) => { setConfig(c); setSaved(JSON.stringify(c)); setTemplates(tpl) })
      .catch(() => setLoadErr(true))
    loadVideos()
  }, [loadVideos])

  const dirty = config !== null && JSON.stringify(config) !== saved
  const invalid = (config?.rules.some((r) => ruleErrors(r).length > 0) ?? false)
    || (config !== null && lightErrors(normalizeLight(config.light)).length > 0)

  async function save() {
    if (!config) return
    setSaving(true); setSaveMsg(null)
    try {
      const c = await vitrineApi.saveConfig(config)
      setConfig(c); setSaved(JSON.stringify(c)); setSaveMsg({ ok: true, text: t("saved") })
    } catch (e) {
      setSaveMsg({ ok: false, text: e instanceof Error ? e.message : String(e) })
    } finally { setSaving(false) }
  }

  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/vitrine" context={t("title")} />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mx-auto max-w-5xl space-y-6">
          <header className="flex flex-wrap items-center gap-3">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#69d7ff]">{t("eyebrow")}</p>
              <h1 className="mt-1 text-xl font-black tracking-tight text-[#e8eef8]">{t("title")}</h1>
            </div>
            <div className="ml-auto flex items-center gap-2">
              {saveMsg && <span className={`text-xs ${saveMsg.ok ? "text-emerald-300" : "text-rose-300"}`}>{saveMsg.text}</span>}
              <button type="button" onClick={() => void save()} disabled={!dirty || invalid || saving}
                className="flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1.5 text-sm font-semibold text-[#69d7ff] disabled:opacity-40">
                <Save size={14} />{saving ? t("saving") : t("save")}
              </button>
            </div>
          </header>

          <StatusCard />
          <MessagesCard />
          <BluetoothCard />

          {loadErr && <p className="rounded-[4px] border border-rose-400/40 bg-rose-400/10 p-3 text-sm text-rose-100">{t("load_error")}</p>}
          {config && <>
            <RuleList rules={config.rules} templates={templates} videos={videos} onChange={(rules) => setConfig({ ...config, rules })} />
            <SettingsCard config={config} onChange={setConfig} />
            <LightCard light={config.light} onChange={(light) => setConfig({ ...config, light })} />
            <DashboardCard config={config} onChange={setConfig} />
          </>}
          <VideoList videos={videos} onChange={loadVideos} />
        </div>
      </main>
    </CockpitShell>
  )
}
