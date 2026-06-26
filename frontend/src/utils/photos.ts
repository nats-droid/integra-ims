import { createClient } from '@/lib/supabase/client'

const BUCKET = 'inspection-photos'

/**
 * Upload a photo file to Supabase Storage.
 * Path format: {companyId}/{eventId}/{timestamp}_{random}.{ext}
 * Returns the storage path (to be stored in photos table) or null on failure.
 */
export async function uploadPhoto(
  file: File,
  companyId: string,
  eventId: string,
): Promise<string | null> {
  const supabase = createClient()
  const fileExt = file.name.split('.').pop() || 'jpg'
  const storagePath = `${companyId}/${eventId}/${Date.now()}_${Math.random().toString(36).slice(2, 8)}.${fileExt}`

  const { error } = await supabase.storage
    .from(BUCKET)
    .upload(storagePath, file, {
      contentType: file.type,
      upsert: false,
    })

  if (error) {
    console.error('Photo upload error:', error)
    return null
  }

  return storagePath
}

/**
 * Get a signed URL for a photo's storage path.
 * Valid for `expiresIn` seconds (default 1 hour).
 * Returns the URL string or null on failure.
 */
export async function getPhotoUrl(
  storagePath: string,
  expiresIn: number = 3600,
): Promise<string | null> {
  const supabase = createClient()
  const { data, error } = await supabase.storage
    .from(BUCKET)
    .createSignedUrl(storagePath, expiresIn)

  if (error || !data) {
    console.error('Signed URL error:', error)
    return null
  }

  return data.signedUrl
}

/**
 * Fetch photos for an inspection event from the photos table,
 * then resolve each to a signed URL.
 * Returns array of { id, storagePath, signedUrl, caption, isCritical }.
 */
export async function getEventPhotos(eventId: string) {
  const supabase = createClient()
  const sb = supabase as any

  const { data: photoRows, error } = await sb
    .from('photos')
    .select('*')
    .eq('related_level', 'event')
    .eq('related_id', eventId)

  if (error || !photoRows) {
    console.error('Fetch photos error:', error)
    return []
  }

  const results = await Promise.all(
    photoRows
      .filter((p: any) => p.storage_path)
      .map(async (p: any) => {
        const signedUrl = await getPhotoUrl(p.storage_path)
        return {
          id: p.id,
          storagePath: p.storage_path,
          signedUrl,
          caption: p.caption,
          isCritical: p.is_critical,
        }
      }),
  )

  return results
}
