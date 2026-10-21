import { MailboxPage } from "./MailboxPage"

export const routes = [{ path: "/mailbox/*", element: <MailboxPage /> }]
export const nav = [
  { path: "/mailbox", icon: "Mail", labelKey: "mailbox", group: "working", roles: [] },
]
export const i18n = {
  de: { mailbox: { title: "Mailbox" } },
  en: { mailbox: { title: "Mailbox" } },
}
