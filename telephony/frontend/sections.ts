import {
  Archive,
  Bot,
  History,
  LayoutDashboard,
  ListTodo,
  Settings2,
  Users,
  type LucideIcon,
} from "lucide-react"
import type { VoIPSection } from "./types"

export interface SectionDefinition {
  id: VoIPSection
  icon: LucideIcon
}

export const sections: SectionDefinition[] = [
  { id: "overview", icon: LayoutDashboard },
  { id: "jobs", icon: ListTodo },
  { id: "calls", icon: History },
  { id: "archive", icon: Archive },
  { id: "agent", icon: Bot },
  { id: "settings", icon: Settings2 },
  { id: "members", icon: Users },
]
