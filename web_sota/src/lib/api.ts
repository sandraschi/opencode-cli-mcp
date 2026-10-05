// Backend base URL. Same-origin ("" -> vite proxies /api to :10951) everywhere
// EXCEPT inside Tauri, where there is no dev proxy and the webview origin is
// tauri.localhost (which the backend CORS config already allows).
// The old hardcoded "http://127.0.0.1:10951" broke every non-localhost
// hostname (CORS): frontend on http://goliath:10950 could never reach it.
function isTauriLike(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as unknown as Record<string, unknown>;
  if (w.__TAURI__ !== undefined || w.__TAURI_INTERNALS__ !== undefined) return true;
  const { protocol, hostname } = window.location;
  return protocol === "tauri:" || hostname === "tauri.localhost" || hostname.endsWith(".tauri.localhost");
}

export const API_BASE = isTauriLike() ? "http://127.0.0.1:10951" : "";
