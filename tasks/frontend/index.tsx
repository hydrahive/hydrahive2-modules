import { TaskBuddyBox } from "./components/TaskBuddyBox"
import { TaskPanel } from "./components/TaskPanel"
import { de } from "./texts.de"
import { en } from "./texts.en"

export const routes = [] as const

export const buddyWidgets = [TaskBuddyBox]

// labelKey: Der Kern übersetzt die Beschriftung des Reiters. Ein Kern, der labelKey nicht kennt, zeigt label.
export const workspaceTabs = [{ id: "tasks", label: "Tasks", labelKey: "tasks:title", component: TaskPanel }]

export const nav = [] as const

// Der Modulname kommt aus tasks:title (Kern shared/nav-label.ts).
export const i18n = { de: { tasks: de }, en: { tasks: en } }
