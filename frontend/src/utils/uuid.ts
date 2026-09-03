/**
 * crypto.randomUUID() only exists in secure contexts (HTTPS or localhost) —
 * on plain HTTP served from an IP address (no DOMAIN/TLS configured yet,
 * see deploy/README.md) it's simply undefined, and calling it throws
 * "crypto.randomUUID is not a function", breaking every button that needs
 * a client-generated id before the server responds (e.g. to open the log
 * stream immediately on submit). This id is only ever used as a
 * correlation id for that stream, never for anything security-sensitive,
 * so Math.random() is an acceptable fallback.
 */
export function randomUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}
