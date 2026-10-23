"use client";

import { useActionState } from "react";
import { PasswordField } from "@/components/FormField/PasswordField";
import { TextField } from "@/components/FormField/TextField";
import { WideButton } from "@/components/WideButton/WideButton";
import { signInWithPassword, type FormState } from "./actions";

export function SignInForm({ callbackUrl, initialError }: { callbackUrl: string; initialError?: string }) {
  const [state, formAction, pending] = useActionState<FormState, FormData>(signInWithPassword, {
    error: initialError,
  });

  return (
    <form className="auth-form" action={formAction} noValidate>
      <input type="hidden" name="callbackUrl" value={callbackUrl} />
      <div className="auth-form__fields">
        <TextField
          name="username"
          label="Username"
          placeholder="Your player name"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          defaultValue={state.values?.username}
        />
        <PasswordField
          name="password"
          label="Password"
          placeholder="Your password"
          autoComplete="current-password"
          required
        />
      </div>
      {state.error && (
        <p className="auth-form__alert" role="alert">
          {state.error}
        </p>
      )}
      <WideButton className="auth-form__submit" label={pending ? "Signing in…" : "Sign in"} disabled={pending} />
    </form>
  );
}
