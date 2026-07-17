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
      title: "Haushaltsbuch",
      subtitle: "Finanzen, Einkäufe und Bonusprogramme an einem Ort",
      dummyBadge: "Platzhalter",
      dummyNote: "Dieses Modul ist ein klar gekennzeichneter Platzhalter. Funktionen und Anbindungen folgen in späteren Ausbaustufen.",
      comingSoon: "Bald verfügbar",
      areas: {
        transactions: {
          name: "Buchungen & Budgets",
          desc: "Einnahmen, Ausgaben und Budgets übersichtlich verwalten.",
        },
        bankImport: {
          name: "Bankimport",
          desc: "Bankbuchungen künftig über unterstützte Importformate übernehmen.",
        },
        lidlPlus: {
          name: "Lidl Plus",
          desc: "Kassenbons und Einkaufsinformationen künftig zusammenführen.",
        },
        payback: {
          name: "PAYBACK",
          desc: "Punktestand und Bonusaktivitäten künftig im Blick behalten.",
        },
      },
    },
  },
  en: {
    haushaltsbuch: {
      title: "Household Budget",
      subtitle: "Finances, shopping and rewards programs in one place",
      dummyBadge: "Placeholder",
      dummyNote: "This module is a clearly marked placeholder. Features and integrations will follow in later stages.",
      comingSoon: "Coming soon",
      areas: {
        transactions: {
          name: "Transactions & Budgets",
          desc: "Manage income, expenses and budgets in one clear overview.",
        },
        bankImport: {
          name: "Bank Import",
          desc: "Import bank transactions through supported formats in the future.",
        },
        lidlPlus: {
          name: "Lidl Plus",
          desc: "Bring receipts and shopping information together in the future.",
        },
        payback: {
          name: "PAYBACK",
          desc: "Keep track of points and rewards activity in the future.",
        },
      },
    },
  },
}
