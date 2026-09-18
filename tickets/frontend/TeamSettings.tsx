import { useState } from "react"
import { ChevronDown, ChevronRight, Plus, UserPlus, Users, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Input } from "@/shared/ui"
import { ticketsApi } from "./api"
import type { Team } from "./types"

interface Props { teams: Team[]; onChanged: () => void }

export function TeamSettings({ teams, onChanged }: Props) {
  const { t } = useTranslation("tickets")
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [member, setMember] = useState("")
  const [error, setError] = useState(false)

  async function createTeam() {
    if (!name.trim()) return
    try {
      await ticketsApi.createTeam(name.trim(), description.trim())
      setName("")
      setDescription("")
      setError(false)
      onChanged()
    } catch {
      setError(true)
    }
  }

  async function addMember(teamId: string) {
    if (!member.trim()) return
    try {
      await ticketsApi.addMember(teamId, member.trim())
      setMember("")
      setError(false)
      onChanged()
    } catch {
      setError(true)
    }
  }

  async function removeMember(teamId: string, userId: string) {
    try {
      await ticketsApi.removeMember(teamId, userId)
      setError(false)
      onChanged()
    } catch {
      setError(true)
    }
  }

  return (
    <section className="shrink-0 border-t border-[#1f2a3b] bg-[#0c131e] p-3">
      <button onClick={() => setOpen((value) => !value)} className="flex w-full items-center gap-2 text-left text-xs font-semibold text-[#a9b5c6] transition-colors hover:text-[#e8eef8]"><Users size={14} className="text-[#69d7ff]" />{t("teams")}<span className="ml-auto rounded-[4px] border border-[#29384d] px-1.5 py-0.5 text-[10px] text-[#718096]">{teams.length}</span>{open ? <ChevronDown size={14} className="text-[#607188]" /> : <ChevronRight size={14} className="text-[#607188]" />}</button>
      {open && <div className="mt-3 space-y-3">
        <div className="space-y-2 rounded-[6px] border border-[#1f2a3b] bg-[#111b29] p-2"><Input value={name} onChange={(event) => setName(event.target.value)} placeholder={t("teamName")} className="border-[#253247] bg-[#0d1420] text-xs" /><div className="flex gap-2"><Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder={t("teamDescription")} className="border-[#253247] bg-[#0d1420] text-xs" /><button onClick={() => void createTeam()} className="grid h-8 w-8 shrink-0 place-items-center rounded-[5px] border border-[#2b4058] text-[#8fa1b8] transition-colors hover:border-[#69d7ff]/60 hover:bg-[#163248] hover:text-[#c8f2ff]" title={t("createTeam")}><Plus size={14} /></button></div></div>
        {error && <p className="rounded-[5px] border border-orange-500/25 bg-orange-500/[7%] px-2 py-1.5 text-[10px] text-orange-200">{t("teamError")}</p>}
        <div className="max-h-52 space-y-2 overflow-y-auto">{teams.map((team) => <div key={team.id} className="rounded-[6px] border border-[#1f2a3b] bg-[#111b29] p-2.5"><div className="flex items-center justify-between gap-2"><span className="truncate text-xs font-semibold text-[#c8d2df]">{team.name}</span><span className="text-[10px] text-[#607188]">{team.members.length}</span></div>{team.description && <p className="mt-1 text-[10px] leading-relaxed text-[#607188]">{team.description}</p>}<div className="mt-2 space-y-1">{team.members.map((item) => <div key={item.user_id} className="flex items-center gap-1.5 text-[10px] text-[#8d9ab0]"><span className="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-[#1d2d42] text-[8px] text-[#a9dff1]">{item.user_id.slice(0, 1).toUpperCase()}</span><span className="min-w-0 flex-1 truncate">{item.user_id}</span><span className="text-[#607188]">{item.role}</span><button onClick={() => void removeMember(team.id, item.user_id)} className="text-[#607188] hover:text-orange-300" title={t("removeMember")}><X size={12} /></button></div>)}</div><div className="mt-2 flex gap-1.5"><Input value={member} onChange={(event) => setMember(event.target.value)} placeholder={t("userId")} className="border-[#253247] bg-[#0d1420] text-[10px]" /><button onClick={() => void addMember(team.id)} className="grid h-8 w-8 shrink-0 place-items-center rounded-[5px] border border-[#253247] text-[#718096] hover:border-[#69d7ff]/60 hover:text-[#c8f2ff]" title={t("addMember")}><UserPlus size={12} /></button></div></div>)}{teams.length === 0 && <p className="py-2 text-center text-[10px] text-[#607188]">{t("noTeams")}</p>}</div>
      </div>}
    </section>
  )
}
