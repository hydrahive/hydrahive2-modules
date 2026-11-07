// Tabs der Projekt-Arbeitsfläche. Ein neuer Tab = neue Datei unter tabs/ + ein Eintrag hier.
import type { LucideIcon } from "lucide-react"
import { FileText, LayoutDashboard } from "lucide-react"
import type { ComponentType } from "react"
import type { GameProject } from "../types"
import { DesignTab } from "./DesignTab"
import { OverviewTab } from "./OverviewTab"

export interface TabProps {
  project: GameProject
  onOpenAgent: () => void
}

export interface WorkspaceTab {
  id: string
  icon: LucideIcon
  labelKey: string
  component: ComponentType<TabProps>
}

export const WORKSPACE_TABS: WorkspaceTab[] = [
  { id: "overview", icon: LayoutDashboard, labelKey: "workspace.tabs.overview", component: OverviewTab },
  { id: "design", icon: FileText, labelKey: "workspace.tabs.design", component: DesignTab },
]

export function tabById(id: string | null): WorkspaceTab {
  return WORKSPACE_TABS.find((tab) => tab.id === id) ?? WORKSPACE_TABS[0]
}
