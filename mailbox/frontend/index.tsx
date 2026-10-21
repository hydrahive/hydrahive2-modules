import { MailboxPage } from "./MailboxPage"

export { i18n } from "./i18n"
export const routes = [{ path: "/mailbox/*", element: <MailboxPage /> }]
export const nav = [
  { path: "/mailbox", icon: "Mail", labelKey: "mailbox", group: "working", roles: [] },
]
