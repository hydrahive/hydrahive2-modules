import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { vitrineApi, type VideoFile, type VitrineConfig } from "./api"
import type { Template } from "./rules"
import { StatusCard } from "./StatusCard"
import { VideoList } from "./VideoList"
import { RuleList } from "./RuleList"
import { DashboardCard } from "./DashboardCard"
import { SettingsCard } from "./SettingsCard"
import { SimulateCard } from "./SimulateCard"
import { MessagesCard } from "./MessagesCard"
import { BluetoothCard } from "./BluetoothCard"
import { LightCard } from "./LightCard"
import { VitrineHeader } from "./VitrineHeader"
import { VitrineTabs } from "./VitrineTabs"
import { dirtyTabs, invalidTabs, tabFromParam, type TabId } from "./tabs"
import { useVitrineStatus } from "./useVitrineStatus"

export function VitrinePage() {
  const { t } = useTranslation("vitrine")
  const [params, setParams] = useSearchParams()
  const tab = tabFromParam(params.get("tab"))
  const select = (id: TabId) => setParams((p) => { const n = new URLSearchParams(p); n.set("tab", id); return n }, { replace: true })
  const { st, light, tick } = useVitrineStatus()
  const [config, setConfig] = useState<VitrineConfig | null>(null)
  const [saved, setSaved] = useState<VitrineConfig | null>(null)
  const [videos, setVideos] = useState<VideoFile[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [loadErr, setLoadErr] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [saving, setSaving] = useState(false)

  const loadVideos = useCallback(() => { vitrineApi.videos().then(setVideos).catch(() => {}) }, [])
  useEffect(() => {
    Promise.all([vitrineApi.config(), vitrineApi.templates()])
      .then(([c, tpl]) => { setConfig(c); setSaved(structuredClone(c)); setTemplates(tpl) })
      .catch(() => setLoadErr(true))
    loadVideos()
  }, [loadVideos])

  const dirty = config ? dirtyTabs(saved, config) : []
  const invalid = config ? invalidTabs(config) : []
  const change = (c: VitrineConfig) => { setConfig(c); setSaveMsg(null) }

  async function save() {
    if (!config) return
    setSaving(true); setSaveMsg(null)
    try {
      const c = await vitrineApi.saveConfig(config)
      setConfig(c); setSaved(structuredClone(c)); setSaveMsg({ ok: true, text: t("saved") })
    } catch (e) {
      setSaveMsg({ ok: false, text: e instanceof Error ? e.message : String(e) })
    } finally { setSaving(false) }
  }

  const needsConfig = tab !== "overview" && tab !== "bluetooth"
  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/vitrine" context={t("title")} />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mx-auto max-w-6xl space-y-4">
          <VitrineHeader st={st} light={light} previewUrl={vitrineApi.previewUrl(tick)} dirty={dirty.length > 0}
            invalid={invalid.length > 0} saving={saving} saveMsg={saveMsg} onSave={() => void save()} />
          <VitrineTabs active={tab} dirty={dirty} invalid={invalid} onSelect={select} />

          {loadErr && needsConfig && <p className="rounded-[4px] border border-rose-400/40 bg-rose-400/10 p-3 text-sm text-rose-100">{t("load_error")}</p>}

          <div role="tabpanel" data-panel={tab}>
            {tab === "overview" && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <StatusCard st={st} tick={tick} />
                <MessagesCard />
              </div>
            )}
            {tab === "program" && config && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
                <RuleList rules={config.rules} templates={templates} videos={videos} onChange={(rules) => change({ ...config, rules })} />
                <div className="space-y-4">
                  <SimulateCard />
                  <VideoList videos={videos} onChange={loadVideos} />
                </div>
              </div>
            )}
            {tab === "display" && config && <SettingsCard config={config} onChange={change} />}
            {tab === "dashboard" && config && <DashboardCard config={config} onChange={change} />}
            {tab === "light" && config && <LightCard light={config.light} status={light} onChange={(l) => change({ ...config, light: l })} />}
            {tab === "bluetooth" && <BluetoothCard />}
          </div>
        </div>
      </main>
    </CockpitShell>
  )
}
