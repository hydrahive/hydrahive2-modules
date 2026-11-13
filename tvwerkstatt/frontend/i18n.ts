// Texte der TV-Werkstatt (de/en). Einfach, ohne Fachwörter des Servers.
const de = {
  tvwerkstatt: {
    title: "TV-Werkstatt",
    subtitle: "Startbildschirm und Zusätze für deinen Fernseher bauen und hinüberschieben.",
    devices: "Fernseher",
    no_devices: "Noch kein Fernseher eingetragen.",
    adb: {
      open: "Debugging offen", closed: "Debugging zu", unauthorized: "Freigabe am Fernseher fehlt", unknown: "nicht geprüft",
    },
    err: {
      general: "Das hat nicht geklappt. Bitte später noch einmal versuchen.",
      tvw_no_incus: "Auf diesem Server gibt es keine Container-Umgebung. Die TV-Werkstatt braucht sie für den Bau.",
    },
  },
}

const en = {
  tvwerkstatt: {
    title: "TV Workshop",
    subtitle: "Build a home screen and add-ons for your TV and push them over.",
    devices: "TVs",
    no_devices: "No TV added yet.",
    adb: {
      open: "Debugging open", closed: "Debugging closed", unauthorized: "Not allowed on the TV yet", unknown: "not checked",
    },
    err: {
      general: "That did not work. Please try again later.",
      tvw_no_incus: "This server has no container environment. The TV Workshop needs it for building.",
    },
  },
}

export const tvwerkstattI18n = { de, en }
