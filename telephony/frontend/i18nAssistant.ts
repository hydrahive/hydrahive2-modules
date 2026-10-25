/** Texte Telefon-Assistent und Notizen (Etappe 2b). Eingebunden in i18n.ts unter voip.assistant / voip.notes. */
export const assistantDe = {
  mode: "Was passiert bei einem Anruf?",
  mode_greeting: "Nur Ansage",
  mode_assistant: "Telefon-Assistent (KI)",
  mode_greeting_help: "HydraHive nimmt ab, spricht die Ansage und legt auf.",
  mode_assistant_help: "Ein KI-Assistent führt das Gespräch: Er nimmt das Anliegen auf und beantwortet Fragen. Danach steht eine Notiz in der Anrufliste.",
  rights: "Anrufer sind Fremde: Der Assistent hat keine Werkzeuge und keinen Zugriff auf Dateien, Mails oder Projekte. Er kennt nur den Text unten und sagt am Anfang, dass eine KI spricht. Ton und Wortlaut werden nicht gespeichert, nur die Notiz.",
  name: "Für wen spricht der Assistent?",
  name_placeholder: "z. B. Max Mustermann oder Beispiel GmbH",
  name_help: "Wird in der Begrüßung genannt: „Hallo, hier ist der digitale Assistent von …“",
  knowledge: "Was der Assistent wissen darf",
  knowledge_placeholder: "z. B. Öffnungszeiten, Adresse, Leistungen, häufige Fragen …",
  knowledge_help: "Nur dieser Text steht dem Assistenten zur Verfügung. Was hier nicht steht, gibt er weiter statt zu raten. {{count}} / 4000 Zeichen.",
  model: "Sprachmodell",
  model_default: "Standard ({{model}})",
  model_help: "Schnelle Modelle sind am Telefon angenehmer. Die Antwortpause liegt meist bei 3–4 Sekunden.",
  save: "Einstellungen speichern",
}

export const notesDe = {
  new: "neue Notiz",
  open_questions: "Offene Fragen",
  needs_review: "Bitte ansehen – ungewöhnliches oder sensibles Anliegen.",
  mark_read: "Als gelesen markieren",
  result: "Ergebnis",
  callback: "Zurückrufen",
}

export type AssistantTexts = typeof assistantDe
export type NotesTexts = typeof notesDe

export const assistantEn: AssistantTexts = {
  mode: "What happens on a call?",
  mode_greeting: "Announcement only",
  mode_assistant: "Phone assistant (AI)",
  mode_greeting_help: "HydraHive picks up, plays the announcement and hangs up.",
  mode_assistant_help: "An AI assistant handles the call: it takes the message and answers questions. Afterwards a note appears in the call list.",
  rights: "Callers are strangers: the assistant has no tools and no access to files, mails or projects. It only knows the text below and says at the start that an AI is speaking. Sound and wording are not stored, only the note.",
  name: "Who does the assistant speak for?",
  name_placeholder: "e.g. Jane Doe or Example Ltd.",
  name_help: "Used in the greeting: “Hello, this is the digital assistant of …”",
  knowledge: "What the assistant may know",
  knowledge_placeholder: "e.g. opening hours, address, services, common questions …",
  knowledge_help: "Only this text is available to the assistant. Anything not in here is passed on instead of guessed. {{count}} / 4000 characters.",
  model: "Language model",
  model_default: "Default ({{model}})",
  model_help: "Fast models feel better on the phone. The answer pause is usually 3–4 seconds.",
  save: "Save settings",
}

export const notesEn: NotesTexts = {
  new: "new note",
  open_questions: "Open questions",
  needs_review: "Please review – unusual or sensitive request.",
  mark_read: "Mark as read",
  result: "Result",
  callback: "Call back",
}
