/** Unicode-safe, URL-safe base64 for sharing programs in the URL hash. */
export function encodeProgram(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function decodeProgram(b64: string): string | null {
  try {
    const norm = b64.replace(/-/g, "+").replace(/_/g, "/");
    const bin = atob(norm + "===".slice((norm.length + 3) % 4));
    const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    return null;
  }
}

export function readHashProgram(): string | null {
  const m = window.location.hash.match(/(?:^#|&)code=([^&]+)/);
  return m ? decodeProgram(m[1]) : null;
}
