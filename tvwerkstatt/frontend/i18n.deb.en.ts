// English texts of the Declutter tab.
export const deb = {
  state: "State", off: "Switched off", by_us: "of these by the workshop", todo: "Recommended, still on",
  backup: "Backup", none: "none yet", read_at: "Last read",
  lists: "Compared with", lists_of: "{{n}} matching of {{all}} lists", no_list: "no matching list",
  never: "Not read yet.", read: "Read from the TV", check_update: "Check after update",
  undo_all: "Undo all", working: "Running … {{step}}",
  back_on: "{{n}} app(s) the workshop had switched off are on again – probably after a firmware update. Tick them "
    + "and switch them off again.",
  step: { container: "Start build environment", lists: "Fetch lists", packages: "Read apps", guard: "Check protection",
    backup: "Save state", batch: "Batch {{n}}", restore: "Putting back", read: "Read state", other: "…" },
  explain: "Apps are only switched off, nothing is deleted. Recommended is what most lists of TVs with the same "
    + "firmware switch off – and none of them keeps on on purpose. Before switching off, the TV itself checks whether "
    + "an app is needed for inputs or settings.",
  title: "Preinstalled apps on \"{{name}}\"", empty: "First \"Read from the TV\".",
  others: "More ({{n}}): already off, disputed or switched off by only a few lists",
  of: "{{of}} of {{n}}", kept: "{{n}}× kept on",
  of_hint: "How many of the matching lists switch the app off or keep it on on purpose.",
  pick_suggested: "Tick recommended ({{n}})", switch_off: "Switch off selected ({{n}})",
  switch_on: "Switch on again ({{n}})",
  confirm_off: "Switch off {{n}} app(s) on the TV now?\n\n{{list}}\n\nNothing is deleted. The state is saved first; "
    + "if something goes wrong, the workshop switches everything from this step on again.",
  confirm_on: "Switch {{n}} app(s) on again?\n\n{{list}}",
  confirm_undo: "Switch on again everything the workshop switched off on this TV ({{n}})?",
  mark: { off: "off", todo: "still on", locked: "locked", on: "on" },
  lock: { core: "Part of Android – always stays on.", home: "Home screen – \"Push to the TV\" and \"Back to the "
    + "original\" take care of it." },
  group: { tracking: "Tracking and remote support", ads: "Ads and content", demo: "Store demo and hotel mode",
    home: "Home screen and screensaver", help: "Help and manuals", other: "Other" },
}

// Fehlertexte des Reiters (werden in err.* eingemischt).
export const debErr = {
  tvw_debloat_blocked: "At least one selected app is needed by the TV for inputs or settings (or could not be "
    + "checked). Nothing was switched off.",
  tvw_debloat_locked: "This app is locked and stays on.",
  tvw_debloat_bad_package: "Please select apps first.",
  tvw_debloat_nothing: "The workshop has not switched anything off on this TV.",
  tvw_debloat_home_changed: "The home screen changed after switching off. Everything from this step is on again.",
  tvw_debloat_not_off: "An app could not be switched off. Everything from this step is on again.",
  tvw_debloat_restore_incomplete: "Putting back did not fully work. Please use \"Undo all\" and \"Check after "
    + "update\".",
  tvw_debloat_not_on: "An app could not be switched on again. Please try again.",
  tvw_debloat_read_failed: "No list of apps could be read from the TV.",
  tvw_debloat_lists_failed: "The cleanyourtv lists could not be read.",
}
