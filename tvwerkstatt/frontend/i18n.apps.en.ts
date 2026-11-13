// English texts of the Apps tab.
export const apps = {
  store_title: "Play Store on the TV", search: "Search", search_ph: "e.g. Kodi, Mediathek …",
  store_hint: "The search opens the Play Store right on the TV. You confirm installing there with the remote – Google "
    + "only allows that on the device.",
  search_bad: "Please use only letters, digits, spaces and . , & ' + - (at most 60 characters).",
  opened: "The Play Store is open on the TV.",
  title: "Self-installed apps on \"{{name}}\"", read: "Read from the TV", read_at: "read {{at}}",
  empty: "First \"Read from the TV\".", off: "switched off", open: "Open in store", uninstall: "Uninstall",
  uninstall_confirm: "Uninstall \"{{name}}\" from the TV now? Its data on the TV will be lost. You can install it "
    + "again from the Play Store.",
  src_store: "Play Store", src_other: "other source", src_locked: "protected",
  preinstalled_hint: "Preinstalled apps are not listed here but under \"Declutter\" (switch off only).",
  job: { store_read: "Reading apps …", store_open: "Opening the Play Store …", store_uninstall: "Uninstalling …" },
}

// Fehlertexte des Reiters (werden in err.* eingemischt).
export const appsErr = {
  tvw_store_bad_query: "Please enter a search text: letters, digits, spaces and . , & ' + -.",
  tvw_store_bad_package: "This app does not exist like that.",
  tvw_store_failed: "The Play Store could not be opened on the TV, or the app could not be removed.",
  tvw_store_locked: "This app is protected (home screen, Play Store or Android itself).",
  tvw_store_not_user_app: "This is a preinstalled app. You can switch it off under \"Declutter\".",
}
