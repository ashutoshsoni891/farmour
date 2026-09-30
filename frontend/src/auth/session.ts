/** Caretaker session token from a single-use login link (owners use Keycloak via oidc.ts). */

const KEY = "farm.caretaker_session";

interface StoredSession {
  token: string;
  expiresAt: number;
}

export function saveCaretakerSession(token: string, expiresInSeconds: number): void {
  const value: StoredSession = { token, expiresAt: Date.now() + expiresInSeconds * 1000 };
  localStorage.setItem(KEY, JSON.stringify(value));
}

export function caretakerToken(): string | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSession;
    if (parsed.expiresAt <= Date.now()) {
      localStorage.removeItem(KEY);
      return null;
    }
    return parsed.token;
  } catch {
    return null;
  }
}

export function clearCaretakerSession(): void {
  localStorage.removeItem(KEY);
}
