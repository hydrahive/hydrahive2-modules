// English texts of the Add-ons tab.
export const add = {
  on_tv: "On \"{{name}}\"", none_yet: "No add-ons from the workshop yet.", catalog: "Catalogue",
  no_catalog: "The catalogue comes from cleanyourtv at a pinned version. Load it once, then it is there.",
  load: "Load catalogue", search: "Search …", working: "Running … {{step}}",
  explain: "Each add-on is built from source in the build environment and installed by the workshop. Add-on install "
    + "scripts do not run and the workshop grants no special permissions – what an add-on needs afterwards is in "
    + "its description. Yellow and red mark permissions that can do more.",
  filter: { all: "All", none: "No permissions", dream: "Screensavers", installed: "Installed" },
  step: { container: "Start build environment", catalog: "Fetch catalogue", fetch: "Fetch source",
    verify: "Check build tools", build: "Build", collect: "Check result", push: "To the TV", remove: "Remove" },
  dream: "Screensaver", installed: "installed", no_perms: "no permissions",
  too_old: "Needs Android {{v}} or newer.", install: "Build & install", rebuild: "Rebuild", remove: "Remove",
  confirm_install: "Build \"{{name}}\" and install it on the TV?\n\nPermissions: {{perms}}\n\nTakes about a "
    + "minute the first time.",
  confirm_remove: "Remove \"{{name}}\" from the TV?",
  perm: { INTERNET: "Internet", ACCESS_NETWORK_STATE: "Network state", SYSTEM_ALERT_WINDOW: "Draw over apps",
    RECEIVE_BOOT_COMPLETED: "Starts at power-on", FOREGROUND_SERVICE: "Runs in background",
    FOREGROUND_SERVICE_SPECIAL_USE: "Background (special use)", FOREGROUND_SERVICE_DATA_SYNC: "Background (sync)",
    WRITE_SECURE_SETTINGS: "Changes system settings", PACKAGE_USAGE_STATS: "Sees app usage",
    ACCESS_COARSE_LOCATION: "Approximate location", BLUETOOTH: "Bluetooth", BLUETOOTH_ADMIN: "Bluetooth control",
    BLUETOOTH_CONNECT: "Bluetooth connect", WAKE_LOCK: "Keeps awake", SCHEDULE_EXACT_ALARM: "Exact alarms" },
}

// Fehlertexte des Reiters (werden in err.* eingemischt).
export const addErr = {
  tvw_addons_catalog_failed: "The catalogue could not be read.",
  tvw_addon_unknown: "This add-on is not in the catalogue.",
  tvw_addon_remove_failed: "The add-on could not be removed.",
}
