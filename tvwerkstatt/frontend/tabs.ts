/** Reiter der Seite, Reihenfolge wie die Klick-Demo. */
export const TABS = ["desktop", "debloat", "addons", "devices", "build"] as const
export type Tab = (typeof TABS)[number]
