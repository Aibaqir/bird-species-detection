const AUTH_KEY = "bird-app-authenticated";

export const LOGIN_EMAIL = "fnfyear@gmail.com";
export const LOGIN_PASSWORD = "@1234";

export function isSignedIn() {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(AUTH_KEY) === "true";
}

export function signIn(email: string, password: string) {
  const valid = email.trim().toLowerCase() === LOGIN_EMAIL && password === LOGIN_PASSWORD;
  if (valid) {
    window.localStorage.setItem(AUTH_KEY, "true");
  }
  return valid;
}

export function signOut() {
  window.localStorage.removeItem(AUTH_KEY);
}
