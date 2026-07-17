import { HaushaltsbuchPage } from "./HaushaltsbuchPage"

export const routes = [
  { path: "/haushaltsbuch", element: <HaushaltsbuchPage /> },
]

export const nav = [
  {
    path: "/haushaltsbuch",
    icon: "WalletCards",
    labelKey: "haushaltsbuch",
    group: "working",
    roles: [] as ("admin" | "user")[],
    cockpit: true,
  },
]

export const i18n = {
  de: {
    haushaltsbuch: {
      haushaltsbuch: "Haushaltsbuch",
      title: "Haushaltsbuch",
      subtitle: "Finanzen, Budgets und Mitglieder gemeinsam verwalten",
    },
  },
  en: {
    haushaltsbuch: {
      haushaltsbuch: "Household Budget",
      title: "Household Budget",
      subtitle: "Manage finances, budgets and members together",
    },
  },
}
