export const MAX_AVATAR_BYTES = 2 * 1024 * 1024;

export type AvatarContentType = "image/png" | "image/jpeg" | "image/webp";

/**
 * Identifies an uploaded image by its leading bytes rather than its file name or the
 * browser-reported type, which the client controls. Only raster formats are accepted:
 * SVG can carry scripts and GIF isn't needed for profile pictures.
 */
export function sniffImageType(bytes: Uint8Array): AvatarContentType | null {
  const starts = (signature: number[], offset = 0) =>
    bytes.length >= offset + signature.length && signature.every((value, i) => bytes[offset + i] === value);

  if (starts([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return "image/png";
  if (starts([0xff, 0xd8, 0xff])) return "image/jpeg";
  // "RIFF" <4-byte size> "WEBP"
  if (starts([0x52, 0x49, 0x46, 0x46]) && starts([0x57, 0x45, 0x42, 0x50], 8)) return "image/webp";
  return null;
}
