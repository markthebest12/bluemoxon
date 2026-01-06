/**
 * Type definitions for book-related data structures.
 */

/**
 * Book image data structure returned from API.
 */
export interface BookImage {
  id: number;
  url: string;
  thumbnail_url: string;
  image_type: string;
  caption: string | null;
  display_order: number;
  is_primary: boolean;
}
