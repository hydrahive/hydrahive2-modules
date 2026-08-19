import { atelierApi } from "./api"
import type { AudioLibraryItem, GalleryItem, VideoJob } from "./types"

/** Bibliothekseintrag in der vom Core erwarteten Form.
 *
 *  Bewusst lokal definiert statt aus dem Core importiert: das Modul soll nicht
 *  gegen Core-Interna bauen. Die Form ist der Vertrag (siehe
 *  features/cockpit/media/mediaRegistry.ts im Core). */
export interface MediaLibraryItem {
  key: string
  kind: "video" | "image" | "audio"
  label: string
  relPath: string
  absPath: string | null
  duration: number | null
}

/** Speist Atelier-Material (Clips, Galeriebilder, Audio) in den Videoschnitt
 *  des Media-Cockpits ein. Der Core sammelt das über gen-modules ein — fehlt das
 *  Atelier, bleibt die Bibliothek einfach leer. */
export const mediaSources = [
  {
    id: "atelier",

    resolveRoot: async (projectId: string): Promise<string | null> => {
      try {
        return (await atelierApi.meta(projectId)).root
      } catch {
        return null
      }
    },

    loadItems: async (projectId: string, root: string | null): Promise<MediaLibraryItem[]> => {
      const [gallery, videos, audio] = await Promise.allSettled([
        atelierApi.gallery(projectId),
        atelierApi.listVideos(projectId),
        atelierApi.audioLibrary(projectId),
      ])
      const items: MediaLibraryItem[] = []

      if (videos.status === "fulfilled") {
        for (const job of videos.value as VideoJob[]) {
          if (job.status !== "completed" || !job.video_rel) continue
          items.push({
            key: `video:${job.video_rel}`,
            kind: "video",
            label: job.prompt?.slice(0, 60) || job.video_rel.split("/").pop() || job.job_id,
            relPath: `atelier/${job.video_rel}`,
            absPath: root ? `${root}/${job.video_rel}` : null,
            duration: job.duration > 0 ? job.duration : null,
          })
        }
      }
      if (gallery.status === "fulfilled") {
        for (const img of gallery.value as GalleryItem[]) {
          items.push({
            key: `image:${img.rel}`,
            kind: "image",
            label: img.name,
            relPath: `atelier/${img.rel}`,
            absPath: img.path || null,
            duration: null,
          })
        }
      }
      if (audio.status === "fulfilled") {
        for (const track of audio.value as AudioLibraryItem[]) {
          items.push({
            key: `audio:${track.rel}`,
            kind: "audio",
            label: track.name,
            relPath: `atelier/${track.rel}`,
            absPath: root ? `${root}/${track.rel}` : null,
            duration: null,
          })
        }
      }
      return items
    },
  },
]
