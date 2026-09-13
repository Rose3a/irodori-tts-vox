import { toBytes } from "fast-base64";

// base64 -> uriのキャッシュ。
const cache = new Map<string, string>();

function detectImageTypeFromBase64(data: string): string {
  // SVG resources may begin with either an XML declaration or the <svg tag.
  if (data.startsWith("PD94bW") || data.startsWith("PHN2Zy")) {
    return "image/svg+xml";
  }
  switch (data[0]) {
    case "/":
      return "image/jpeg";
    case "R":
      return "image/gif";
    case "i":
      return "image/png";
    case "U":
      return "image/webp";
    default:
      throw new Error("Unsupported image type");
  }
}

export const base64ToUri = async (data: string, type: string) => {
  const cached = cache.get(data);
  if (cached) {
    return cached;
  }
  const buffer = await toBytes(data);
  const url = URL.createObjectURL(new Blob([new Uint8Array(buffer)], { type }));
  cache.set(data, url);
  return url;
};

export async function base64ImageToUri(image: string): Promise<string> {
  const mimeType = detectImageTypeFromBase64(image);
  return await base64ToUri(image, mimeType);
}
