/** Texte für Erzeugen und Aufträge (Etappe 3). Ohne Terminal-, Datei- oder Einstellungs-Hinweise (Grundregel). */

export const jobs_de = {
  image: "Bild",
  image_none: "Noch kein Bild. Die KI erzeugt es aus der Beschreibung, der Kamera, dem Look und den Bausteinen.",
  image_generate: "Bild erzeugen",
  image_again: "Weiteres Bild erzeugen",
  image_running: "Bild wird erzeugt …",
  image_choose: "Dieses Bild verwenden",
  notice_image_started: "Bild wird erzeugt. Das dauert meist unter einer Minute.",
  job_err: {
    no_key: "Für Bilder ist kein Anbieter eingerichtet. Das geht in der Admin-Konsole unter KI-Modelle.",
    provider_rejected: "Der Anbieter hat die Anfrage abgelehnt. Bitte im Drehbuch unter „Modelle“ ein anderes Bild-Modell eintragen oder später erneut versuchen.",
    provider_unreachable: "Der Anbieter ist gerade nicht erreichbar. Bitte später erneut versuchen.",
    empty_answer: "Der Anbieter hat kein Bild geliefert. Bitte erneut versuchen.",
    bad_image: "Die Antwort des Anbieters war kein gültiges Bild. Bitte erneut versuchen.",
    interrupted: "Der Auftrag wurde unterbrochen (Neustart). Bitte erneut starten.",
    shot_gone: "Der Shot wurde inzwischen gelöscht.",
    internal: "Etwas ist schiefgegangen. Bitte erneut versuchen.",
  },
}

export const jobs_en: typeof jobs_de = {
  image: "Image",
  image_none: "No image yet. The AI creates it from the description, the camera, the look and the elements.",
  image_generate: "Create image",
  image_again: "Create another image",
  image_running: "Creating image …",
  image_choose: "Use this image",
  notice_image_started: "Creating image. This usually takes less than a minute.",
  job_err: {
    no_key: "No provider for images is set up. You can do that in the admin console under AI models.",
    provider_rejected: "The provider rejected the request. Please enter another image model in the screenplay under “Models” or try again later.",
    provider_unreachable: "The provider cannot be reached right now. Please try again later.",
    empty_answer: "The provider returned no image. Please try again.",
    bad_image: "The provider's answer was not a valid image. Please try again.",
    interrupted: "The job was interrupted (restart). Please start it again.",
    shot_gone: "The shot has been deleted in the meantime.",
    internal: "Something went wrong. Please try again.",
  },
}
