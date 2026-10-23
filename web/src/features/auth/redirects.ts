export const DEFAULT_AFTER_SIGN_IN = "/explore";

/**
 * Only same-site destinations are allowed after sign-in (no open redirects).
 * Relative paths pass through; absolute URLs (as Auth.js sends from the proxy) are
 * reduced to their path when their host matches `currentHost`.
 */
export function safeRedirectPath(candidate: string | null | undefined, currentHost?: string | null): string {
  if (!candidate || candidate.includes("\\")) return DEFAULT_AFTER_SIGN_IN;
  if (candidate.startsWith("/")) {
    return candidate.startsWith("//") ? DEFAULT_AFTER_SIGN_IN : candidate;
  }
  try {
    const url = new URL(candidate);
    if ((url.protocol === "http:" || url.protocol === "https:") && currentHost && url.host === currentHost) {
      return `${url.pathname}${url.search}${url.hash}`;
    }
  } catch {
    // Not a URL; fall through to the default.
  }
  return DEFAULT_AFTER_SIGN_IN;
}

/** Messages for Auth.js `?error=` codes on the sign-in page. Unknown codes get a generic message. */
export function signInErrorMessage(code: string | undefined): string | undefined {
  switch (code) {
    case undefined:
      return undefined;
    case "OAuthAccountNotLinked":
      return "This Google account's email already belongs to a LocalQuest account that uses a username and password. Sign in with your username and password instead.";
    case "AccessDenied":
      return "Google sign-in was not allowed. Use a Google account with a verified email address.";
    case "CredentialsSignin":
      return "That username and password don't match. Try again.";
    default:
      return "Sign-in didn't work. Please try again.";
  }
}
