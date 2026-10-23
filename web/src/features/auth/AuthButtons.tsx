import { WideButton } from "@/components/WideButton/WideButton";
import { signInWithGoogle, signOutAction } from "./actions";

/** "or continue with" divider followed by the Google button, as in the sign-up frame. */
export function GoogleSignIn({ callbackUrl }: { callbackUrl: string }) {
  return (
    <>
      <div className="auth-divider">
        <span>or continue with</span>
      </div>
      <form action={signInWithGoogle} className="auth-google">
        <input type="hidden" name="callbackUrl" value={callbackUrl} />
        <WideButton label="Continue with Google" size="secondary" />
      </form>
    </>
  );
}

export function SignOutButton({ variant = "small" }: { variant?: "small" | "wide" }) {
  return (
    <form action={signOutAction}>
      {variant === "wide" ? (
        <WideButton label="Sign out" size="secondary" />
      ) : (
        <button type="submit" className="small-button">
          Sign out
        </button>
      )}
    </form>
  );
}
