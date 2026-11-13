import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { BuildPanel } from "./BuildPanel"
import { type AddonsActions, AddonsTab } from "./AddonsTab"
import { type AppsActions, AppsTab } from "./AppsTab"
import { type DebloatActions, DebloatTab } from "./DebloatTab"
import { DesktopTab, type DesktopActions } from "./DesktopTab"
import { moodAt } from "./desktopLogic"
import { DevicePanel, type DeviceActions } from "./DevicePanel"
import { anyChecking, installConfirmKey } from "./deviceLogic"
import { errorKey } from "./logic"
import { SetupPanel, type SetupActions } from "./SetupPanel"
import { setupView } from "./setupLogic"
import { type Tab, TABS } from "./tabs"
import { BOX, BOX_HEAD, INPUT, MUTED, TAB, TAB_ON } from "./ui"
import { useWorkshop } from "./useWorkshop"

/** Modulseite TV-Werkstatt (nur Admins). Aufbau wie die Klick-Demo: Reiter, Desktop in drei Spalten. */
export function TvWerkstattPage() {
  const { t } = useTranslation("tvwerkstatt")
  const w = useWorkshop()
  const [tab, setTab] = useState<Tab>("desktop")
  const [picked, setPicked] = useState<{ id: string; set: Set<string> }>({ id: "", set: new Set() })
  const [now, setNow] = useState(() => new Date())
  const [mood, setMood] = useState(() => moodAt(new Date().getHours()))
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 30_000); return () => clearInterval(id) }, [])
  const id = w.deviceId ?? ""
  const sel = picked.id === id ? picked.set : new Set<string>()
  const list = (p: string[]) => p.map((x) => `• ${x}`).join("\n")
  const appsAct: AppsActions = {
    onRead: () => w.act(() => api.readStore(id)),
    onOpen: (pkg) => w.act(() => api.openStore(id, { package: pkg })),
    onSearch: (q) => w.act(() => api.openStore(id, { query: q })),
    onUninstall: (pkg) => {
      const name = w.desk?.apps.find((a) => a.package === pkg)?.label || pkg
      if (window.confirm(t("apps.uninstall_confirm", { name }))) w.act(() => api.uninstallApp(id, pkg))
    },
  }
  const addonsAct: AddonsActions = {
    onCatalog: () => w.act(() => api.loadCatalog(id)),
    onInstall: (a) => {
      const perms = (a.installed ? a.installed.permissions : a.permissions.map((p) => p.name))
        .map((n) => t(`add.perm.${n}`, { defaultValue: n })).join(", ") || t("add.no_perms")
      if (window.confirm(t("add.confirm_install", { name: a.name, perms }))) w.act(() => api.installAddon(id, a.id))
    },
    onRemove: (a) => {
      if (window.confirm(t("add.confirm_remove", { name: a.name }))) w.act(() => api.removeAddon(id, a.id))
    },
  }
  const debloat: DebloatActions = {
    onRead: () => w.act(() => api.readDebloat(id)),
    onPick: (pkgs, on) => setPicked(() => {
      const next = new Set(sel); pkgs.forEach((p) => (on ? next.add(p) : next.delete(p))); return { id, set: next }
    }),
    onOff: (p) => {
      if (window.confirm(t("deb.confirm_off", { n: p.length, list: list(p) })))
        w.act(() => api.debloatOff(id, p), () => setPicked({ id, set: new Set() }))
    },
    onOn: (p) => {
      if (window.confirm(t("deb.confirm_on", { n: p.length, list: list(p) })))
        w.act(() => api.debloatOn(id, p), () => setPicked({ id, set: new Set() }))
    },
    onUndoAll: () => {
      if (window.confirm(t("deb.confirm_undo", { n: w.deb?.view?.ours.length ?? 0 }))) w.act(() => api.debloatOn(id))
    },
  }

  const setup: SetupActions = {
    onSetup: (accept) => w.act(() => api.startSetup(accept)),
    onStop: () => w.act(api.stopContainer),
    onRemove: () => { if (window.confirm(t("setup.remove_confirm"))) w.act(api.removeContainer) },
  }
  const devices: DeviceActions = {
    onAdd: (name, address) => w.act(() => api.addDevice(name.trim(), address.trim())),
    onCheck: (d) => w.act(() => api.checkDevice(d)),
    onRemove: (d) => { if (window.confirm(t("device.remove_confirm"))) w.act(() => api.removeDevice(d)) },
    onInstall: (d) => {
      if (window.confirm(t(installConfirmKey(w.s?.devices.find((x) => x.device_id === d))))) w.act(() => api.installHome(d))
    },
    onRestore: (d) => { if (window.confirm(t("install.restore_confirm"))) w.act(() => api.restoreHome(d)) },
  }
  const desktop: DesktopActions = {
    onLook: w.editDraft,
    onSave: () => { if (w.draft) w.act(() => api.saveLook(id, w.draft!), w.clearDirty) },
    onReadApps: () => w.act(() => api.readApps(id)),
    onPushLook: () => {
      if (!w.draft || !window.confirm(t("desk.push_confirm"))) return
      w.act(async () => { await api.saveLook(id, w.draft!); w.clearDirty(); return api.pushLook(id) })
    },
    onBuild: () => w.act(api.startBuild),
    onInstall: () => devices.onInstall(id),
    onRestore: () => devices.onRestore(id),
    onMood: setMood,
    onUpload: (m, f) => w.act(() => api.uploadWallpaper(id, m, f)),
    onDeleteWall: (wid) => { if (window.confirm(t("desk.remove_image_confirm"))) w.act(() => api.deleteWallpaper(id, wid)) },
  }
  return <PageView s={w.s} msg={w.msg} busy={w.busy} tab={tab} onTab={setTab} deviceId={w.deviceId}
    onDevice={w.setDeviceId} desk={w.desk} deb={w.deb} debloat={debloat} picked={sel} store={w.store} apps={appsAct}
    addons={w.addons} addonsAct={addonsAct}
    draft={w.draft} mood={mood} now={now}
    setup={setup} devices={devices} desktop={desktop} onBuild={() => w.act(api.startBuild)} />
}

const NOOP_ADDONS: AddonsActions = { onCatalog: () => {}, onInstall: () => {}, onRemove: () => {} }
const NOOP_APPS: AppsActions = { onRead: () => {}, onOpen: () => {}, onSearch: () => {}, onUninstall: () => {} }
const NOOP_DEBLOAT: DebloatActions = { onRead: () => {}, onPick: () => {}, onOff: () => {}, onOn: () => {},
  onUndoAll: () => {} }
const NOOP_SETUP: SetupActions = { onSetup: () => {}, onStop: () => {}, onRemove: () => {} }
const NOOP_DEVICES: DeviceActions = {
  onAdd: () => {}, onCheck: () => {}, onRemove: () => {}, onInstall: () => {}, onRestore: () => {},
}

/** Reine Ansicht: Zustand rein, Seite raus (getrennt, damit sie ohne Server testbar ist). */
export function PageView(p: {
  s: api.TvwState | null; msg: string | null; busy?: boolean; tab?: Tab; onTab?: (t: Tab) => void
  deviceId?: string | null; onDevice?: (id: string) => void; desk?: api.TvwDesktop | null; draft?: api.TvwLook | null
  deb?: api.TvwDebloat | null; debloat?: DebloatActions; picked?: Set<string>; store?: api.TvwStore | null
  apps?: AppsActions; addons?: api.TvwAddons | null; addonsAct?: AddonsActions
  mood?: api.Mood; now?: Date; setup?: SetupActions; devices?: DeviceActions; desktop?: DesktopActions
  onBuild?: () => void
}) {
  const { t } = useTranslation("tvwerkstatt")
  const { s, msg, busy = false, tab = "desktop" } = p
  const ready = !!s && s.container !== "missing" && setupView(s.setup, s.container) !== "running"
  const working = busy || !!s && (anyChecking(s.devices) || s.build?.state === "running")
  const dev = s?.devices.find((d) => d.device_id === p.deviceId)
  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4">
      <header className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-[#e8eef8]">{t("title")}</h1>
        {s?.incus && s.devices.length > 0 && (
          <select className={`${INPUT} w-auto`} aria-label={t("desk.choose")} value={p.deviceId ?? ""}
            onChange={(e) => p.onDevice?.(e.target.value)}>
            {s.devices.map((d) => <option key={d.device_id} value={d.device_id}>{d.name} · {d.address}</option>)}
          </select>
        )}
        <p className={`${MUTED} basis-full`}>{t("subtitle")}</p>
      </header>
      {msg && <p className="text-sm text-red-300" role="alert">{t(msg)}</p>}
      {!s && !msg && <p className={MUTED}>…</p>}
      {s && !s.incus && <p className="text-sm text-amber-200">{t(errorKey(s.error_code))}</p>}
      {s?.incus && (
        <nav className="flex flex-wrap gap-1 border-b border-[rgb(var(--hh-s-rand,52_66_92))]" role="tablist">
          {TABS.map((k) => (
            <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => p.onTab?.(k)}
              className={tab === k ? TAB_ON : TAB}>{t(`tab.${k}`)}</button>
          ))}
        </nav>
      )}
      {s?.incus && tab === "desktop" && (
        !ready ? <Hint text={t("desk.need_setup")} />
          : !dev ? <Hint text={t("desk.need_device")} />
            : !p.desk || !p.draft ? <p className={MUTED}>…</p>
              : <DesktopTab s={s} dev={dev} desk={p.desk} draft={p.draft} mood={p.mood ?? "evening"}
                now={p.now ?? new Date()} busy={working} actions={p.desktop!} />
      )}
      {s?.incus && tab === "debloat" && (
        !ready ? <Hint text={t("desk.need_setup")} />
          : !dev ? <Hint text={t("desk.need_device")} />
            : <DebloatTab dev={dev} data={p.deb ?? null} picked={p.picked ?? new Set()} busy={working}
              actions={p.debloat ?? NOOP_DEBLOAT} />
      )}
      {s?.incus && tab === "apps" && (
        !ready ? <Hint text={t("desk.need_setup")} />
          : !dev ? <Hint text={t("desk.need_device")} />
            : <AppsTab dev={dev} data={p.store ?? null} desk={p.desk ?? null} busy={working}
              actions={p.apps ?? NOOP_APPS} />
      )}
      {s?.incus && tab === "addons" && (
        !ready ? <Hint text={t("desk.need_setup")} />
          : !dev ? <Hint text={t("desk.need_device")} />
            : <AddonsTab dev={dev} data={p.addons ?? null} busy={working} actions={p.addonsAct ?? NOOP_ADDONS} />
      )}
      {s?.incus && tab === "devices" && (
        <DevicePanel devices={s.devices} ready={ready} busy={working} hasBuild={s.builds.some((b) => b.state === "done")}
          actions={p.devices ?? NOOP_DEVICES} />
      )}
      {s?.incus && tab === "build" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <SetupPanel job={s.setup} container={s.container} busy={busy} actions={p.setup ?? NOOP_SETUP} />
          <BuildPanel job={s.build} builds={s.builds} ready={ready} busy={working} onBuild={p.onBuild ?? (() => {})} />
        </div>
      )}
    </div>
  )
}

function Hint({ text }: { text: string }) {
  return <section className={BOX}><h2 className={BOX_HEAD}>{text}</h2></section>
}
