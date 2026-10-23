import { useState } from "react"
import { useTranslation } from "react-i18next"
import { KeyRound } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { MsAppDialog } from "./MsAppDialog"

/** Nur für Admins: Knopf „Microsoft-Anmeldung einrichten“ (Client-ID einmal global für alle Nutzer). */
export function MsAppButton() {
  const { t } = useTranslation("mailbox")
  const role = useAuthStore((s) => s.role)
  const [open, setOpen] = useState(false)
  if (role !== "admin") return null
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} title={t("app.title")} aria-label={t("app.title")} data-mbx-ms-app-open="1"
        className="rounded-[4px] border border-[#2a364b] px-2 py-1.5 text-[#8d9ab0] hover:text-[#e8eef8]"><KeyRound size={14} /></button>
      {open && <MsAppDialog onClose={() => setOpen(false)} />}
    </>
  )
}
