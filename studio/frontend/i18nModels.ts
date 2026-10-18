/** Texte für die Modellwahl im Drehbuch (Katalog des Kerns). Ohne Terminal-, Datei- oder Einstellungs-Hinweise. */

export const models_de = {
  gen: { video: "Video", image: "Bild", voice: "Sprache", music: "Musik", text: "Text (KI-Regie)" },
  model_default: "Standard ({{model}})",
  model_auto: "automatisch",
  model_search: "Modell suchen …",
  model_search_for: "{{what}}: Modell suchen",
  model_group_cloud: "Cloud",
  model_group_local: "Lokal · {{device}}",
  model_local_device: "eigene GPU",
  model_group_kept: "Bisher gewählt (nicht mehr im Katalog)",
  model_catalog_empty: "Der Modellkatalog hat dafür gerade keine Einträge. Du kannst die Modell-ID eintragen oder das Feld leer lassen.",
}

export const models_en: typeof models_de = {
  gen: { video: "Video", image: "Image", voice: "Voice", music: "Music", text: "Text (AI director)" },
  model_default: "Default ({{model}})",
  model_auto: "automatic",
  model_search: "Search model …",
  model_search_for: "{{what}}: search model",
  model_group_cloud: "Cloud",
  model_group_local: "Local · {{device}}",
  model_local_device: "own GPU",
  model_group_kept: "Chosen before (no longer in the catalogue)",
  model_catalog_empty: "The model catalogue has no entries for this right now. You can enter the model ID or leave the field empty.",
}
