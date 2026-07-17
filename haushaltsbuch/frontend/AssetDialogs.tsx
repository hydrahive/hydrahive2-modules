import { useState, type FormEvent } from "react"
import { FolderTree, Landmark } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage, haushaltsbuchApi, isConflict } from "./api"
import { parseMinorUnits } from "./money"
import type { Account, AccountType, Category, CategoryKind, Household, Member } from "./types"
import { Button, ErrorState, Field, Input, Select } from "./ui"

const accountTypes: [AccountType, string][] = [["checking", "Girokonto"], ["savings", "Tages-/Sparkonto"], ["cash", "Bargeld"], ["credit_card", "Kreditkarte"], ["wallet", "PayPal/Wallet"], ["liability", "Darlehen/Verbindlichkeit"], ["asset", "Wertkonto/Depot"], ["custom", "Benutzerdefiniert"]]

export function AccountDialog({ household, members, account, onClose, onSaved }: { household: Household; members: Member[]; account?: Account; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(account?.name ?? "")
  const [type, setType] = useState<AccountType>(account?.type ?? "checking")
  const [owner, setOwner] = useState(account?.owner_member_id ? String(account.owner_member_id) : "")
  const [currency, setCurrency] = useState(account?.currency ?? household.base_currency)
  const [bankId, setBankId] = useState(account?.bank_identifier ?? "")
  const [opening, setOpening] = useState("")
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>()
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(undefined); try {
    if (account) await haushaltsbuchApi.updateAccount(account.id, { name: name.trim(), type, owner_member_id: owner ? Number(owner) : null, bank_identifier: bankId.trim() || null, archived: account.archived, revision: account.revision })
    else await haushaltsbuchApi.createAccount({ name: name.trim(), type, owner_member_id: owner ? Number(owner) : null, currency, bank_identifier: bankId.trim() || null, opening_balance: opening ? parseMinorUnits(opening, currency) : 0 })
    onSaved()
  } catch (cause) { setError(cause) } finally { setBusy(false) } }
  return <AdminDialog title={account ? "Konto bearbeiten" : "Konto anlegen"} eyebrow="Haushaltsbuch · Konten" icon={<Landmark size={16} />} onClose={busy ? undefined : onClose} footer={<><Button onClick={onClose} disabled={busy}>Abbrechen</Button><Button tone="primary" type="submit" form="account-form" disabled={busy}>{busy ? "Speichert …" : "Speichern"}</Button></>}><form id="account-form" onSubmit={submit} className="grid gap-4">{error !== undefined && <ErrorState error={errorMessage(error)} conflict={isConflict(error)} />}<Field label="Name"><Input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></Field><div className="grid gap-4 sm:grid-cols-2"><Field label="Kontotyp"><Select value={type} onChange={(e) => setType(e.target.value as AccountType)}>{accountTypes.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select></Field><Field label="Kontoinhaber"><Select value={owner} onChange={(e) => setOwner(e.target.value)}><option value="">Gemeinsam</option>{members.map((member) => <option key={member.id} value={member.id}>{member.username}</option>)}</Select></Field></div><div className="grid gap-4 sm:grid-cols-2"><Field label="Währung"><Input required maxLength={3} disabled={!!account} value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} /></Field><Field label="Maskierte Bankkennung" hint="Zum Beispiel •••• 1234"><Input maxLength={64} value={bankId} onChange={(e) => setBankId(e.target.value)} /></Field></div>{!account && <Field label={`Anfangssaldo (${currency})`} hint={currency !== household.base_currency ? "Fremdwährungs-Eröffnungssalden müssen später als Buchung erfasst werden." : "Wird als eigener Eröffnungsvorgang gebucht."}><Input inputMode="decimal" value={opening} onChange={(e) => setOpening(e.target.value)} placeholder="0,00" /></Field>}</form></AdminDialog>
}

export function CategoryDialog({ categories, category, onClose, onSaved }: { categories: Category[]; category?: Category; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(category?.name ?? "")
  const [kind, setKind] = useState<CategoryKind>(category?.kind ?? "expense")
  const [parent, setParent] = useState(category?.parent_id ? String(category.parent_id) : "")
  const [color, setColor] = useState(category?.color ?? "#546E7A")
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>()
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(undefined); const body = { name: name.trim(), kind, parent_id: parent ? Number(parent) : null, icon: category?.icon ?? null, color, sort_order: category?.sort_order ?? 0 }; try { if (category) await haushaltsbuchApi.updateCategory(category.id, { ...body, archived: category.archived, revision: category.revision }); else await haushaltsbuchApi.createCategory(body); onSaved() } catch (cause) { setError(cause) } finally { setBusy(false) } }
  const parents = categories.filter((item) => item.id !== category?.id && item.kind === kind && !item.archived)
  return <AdminDialog title={category ? "Kategorie bearbeiten" : "Kategorie anlegen"} eyebrow="Haushaltsbuch · Kategorien" icon={<FolderTree size={16} />} onClose={busy ? undefined : onClose} footer={<><Button onClick={onClose} disabled={busy}>Abbrechen</Button><Button tone="primary" type="submit" form="category-form" disabled={busy}>{busy ? "Speichert …" : "Speichern"}</Button></>}><form id="category-form" onSubmit={submit} className="grid gap-4">{error !== undefined && <ErrorState error={errorMessage(error)} conflict={isConflict(error)} />}<Field label="Name"><Input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></Field><div className="grid gap-4 sm:grid-cols-2"><Field label="Art"><Select value={kind} onChange={(e) => { setKind(e.target.value as CategoryKind); setParent("") }}><option value="expense">Ausgabe</option><option value="income">Einnahme</option></Select></Field><Field label="Übergeordnete Kategorie"><Select value={parent} onChange={(e) => setParent(e.target.value)}><option value="">Keine</option>{parents.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></Field></div><Field label="Farbe"><Input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-10 p-1" /></Field></form></AdminDialog>
}
