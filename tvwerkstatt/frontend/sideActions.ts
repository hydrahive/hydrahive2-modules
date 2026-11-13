import type { TFunction } from "i18next"
import type { AddonsActions } from "./AddonsTab"
import type { AppDeviceActions } from "./AppDevicesPanel"
import type { AppsActions } from "./AppsTab"
import * as api from "./api"
import { downloadApk } from "./download"
import type { useWorkshop } from "./useWorkshop"

/** Handgriffe der Reiter Apps, Zusätze und der HydraHive-App (ausgelagert, damit die Seite klein bleibt). */
export function sideActions(w: ReturnType<typeof useWorkshop>, id: string, t: TFunction<"tvwerkstatt">,
  setCode: (c: api.TvwAppCode) => void): { appsAct: AppsActions; appAct: AppDeviceActions; addonsAct: AddonsActions } {
  const appsAct: AppsActions = {
    onRead: () => w.act(() => api.readStore(id)),
    onOpen: (pkg) => w.act(() => api.openStore(id, { package: pkg })),
    onSearch: (q) => w.act(() => api.openStore(id, { query: q })),
    onUninstall: (pkg) => {
      const name = w.desk?.apps.find((a) => a.package === pkg)?.label || pkg
      if (window.confirm(t("apps.uninstall_confirm", { name }))) w.act(() => api.uninstallApp(id, pkg))
    },
  }
  const appAct: AppDeviceActions = {
    onCode: (name) => w.act(() => api.newAppCode(name).then(setCode)),
    onRevoke: (a) => {
      const name = w.appDevs.devices.find((d) => d.app_id === a)?.name ?? a
      if (window.confirm(t("app.revoke_confirm", { name }))) w.act(() => api.revokeApp(a))
    },
    onRemove: (a) => w.act(() => api.removeApp(a)),
    onNotice: (a, title, body, buttons) => w.act(() => api.sendAppNotice(a, title, body, buttons)),
    onBuild: () => w.act(api.buildApp),
    onDownload: () => w.act(() => downloadApk(api.APP_APK_URL)),
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
  return { appsAct, appAct, addonsAct }
}
