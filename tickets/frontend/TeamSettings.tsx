import { useState } from "react"
import { ChevronDown, ChevronRight, Plus, UserPlus, Users, X } from "lucide-react"
import { useTranslation } from "react-i18next"
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
    try { await ticketsApi.createTeam(name.trim(), description.trim()); setName(""); setDescription(""); setError(false); onChanged() } catch { setError(true) }
  }
  async function addMember(teamId: string) {
    if (!member.trim()) return
    try { await ticketsApi.addMember(teamId, member.trim()); setMember(""); setError(false); onChanged() } catch { setError(true) }
  }
  async function removeMember(teamId: string, userId: string) {
    try { await ticketsApi.removeMember(teamId, userId); setError(false); onChanged() } catch { setError(true) }
  }

  return (
    <section className="border-t border-white/10 bg-zinc-950/40 p-3">
      <button onClick={() => setOpen((value) => !value)} className="flex w-full items-center gap-2 text-left text-sm font-medium text-zinc-300"><Users size={15} className="text-sky-400" />{t("teams")} {open ? <ChevronDown size={14} className="ml-auto" /> : <ChevronRight size={14} className="ml-auto" />}</button>
      {open && <div className="mt-3 space-y-3"><div className="flex gap-2"><input value={name} onChange={(event) => setName(event.target.value)} placeholder={t("teamName")} className="min-w-0 flex-1 rounded-lg border border-white/10 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200" /><button onClick={() => void createTeam()} className="rounded-lg bg-sky-500/20 p-2 text-sky-300" title={t("createTeam")}><Plus size={14} /></button></div>{error && <p className="text-xs text-red-300">{t("teamError")}</p>}<div className="space-y-2">{teams.map((team) => <div key={team.id} className="rounded-lg bg-white/[3%] px-2 py-2 text-xs text-zinc-400"><div className="font-medium text-zinc-200">{team.name}</div><div className="mt-1 space-y-1">{team.members.map((item) => <div key={item.user_id} className="flex items-center gap-1"><span className="min-w-0 flex-1 truncate">{item.user_id}</span><span className="text-zinc-600">{item.role}</span><button onClick={() => void removeMember(team.id, item.user_id)} className="text-zinc-600 hover:text-red-300"><X size={12} /></button></div>)}</div><div className="mt-2 flex gap-1"><input value={member} onChange={(event) => setMember(event.target.value)} placeholder={t("userId")} className="min-w-0 flex-1 rounded border border-white/10 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-300" /><button onClick={() => void addMember(team.id)} className="rounded bg-white/5 p-1 text-zinc-400 hover:text-sky-300" title={t("addMember")}><UserPlus size={12} /></button></div></div>)}{teams.length === 0 && <p className="text-xs text-zinc-600">{t("noTeams")}</p>}</div></div>}
    </section>
  )
}
