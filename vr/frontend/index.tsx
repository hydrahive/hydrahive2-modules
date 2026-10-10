import { VrPage } from "./VrPage"

export const routes = [{ path: "/vr", element: <VrPage /> }]

export const nav = [
  { path: "/vr", icon: "Glasses", labelKey: "vr", group: "working", roles: [] as ("admin" | "user")[] },
]

export const i18n = {
  de: {
    vr: {
      title: "VR-Brillen", subtitle: "HydraVR auf der Meta Quest mit deinem Zugang verbinden.",
      pair_button: "Brille koppeln", pair_title: "Neue Brille koppeln", headset_name: "Name der Brille",
      pair_create: "QR-Code erzeugen",
      step1: "1. In der Brille HydraVR öffnen und „📷 QR-Code scannen“ antippen.",
      step2: "2. Diesen QR-Code ein paar Sekunden aus 30–60 cm anschauen. Fertig.",
      valid_for: "gültig noch {{time}}, nur einmal verwendbar", code: "Code", expired: "Abgelaufen",
      pinned: "Server-Zertifikat ist im QR hinterlegt – die Brille vertraut genau diesem Server.",
      no_key_in_qr: "Der QR enthält keinen Zugangsschlüssel, nur einen Einmal-Code.",
      new_code: "Neuer Code", close: "Schließen", headsets: "Gekoppelte Brillen", online: "{{count}} verbunden",
      empty: "Noch keine Brille gekoppelt.", paired_at: "gekoppelt {{time}}", remove: "Entfernen",
      remove_confirm: "„{{name}}“ entfernen? Die Brille verliert sofort den Zugang und muss neu gekoppelt werden.",
    },
  },
  en: {
    vr: {
      title: "VR headsets", subtitle: "Connect HydraVR on the Meta Quest to your account.",
      pair_button: "Pair headset", pair_title: "Pair a new headset", headset_name: "Headset name",
      pair_create: "Create QR code",
      step1: "1. Open HydraVR in the headset and tap “📷 Scan QR code”.",
      step2: "2. Look at this QR code for a few seconds from 30–60 cm. Done.",
      valid_for: "valid for {{time}}, single use", code: "Code", expired: "Expired",
      pinned: "Server certificate is embedded – the headset trusts exactly this server.",
      no_key_in_qr: "The QR contains no access key, only a one-time code.",
      new_code: "New code", close: "Close", headsets: "Paired headsets", online: "{{count}} connected",
      empty: "No headset paired yet.", paired_at: "paired {{time}}", remove: "Remove",
      remove_confirm: "Remove “{{name}}”? The headset loses access immediately and must be paired again.",
    },
  },
}
