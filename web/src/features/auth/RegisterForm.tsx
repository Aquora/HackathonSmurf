"use client";

import { useActionState } from "react";
import { PasswordField } from "@/components/FormField/PasswordField";
import { TextField } from "@/components/FormField/TextField";
import { WideButton } from "@/components/WideButton/WideButton";
import { PASSWORD_RULES } from "@/lib/validation";
import { registerAccount, type FormState } from "./actions";

export function RegisterForm() {
  const [state, formAction, pending] = useActionState<FormState, FormData>(registerAccount, {});

  return (
    <form className="auth-form" action={formAction} noValidate>
      <div className="auth-form__fields">
        <TextField
          name="username"
          label="Username"
          placeholder="Choose your player name"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          minLength={3}
          maxLength={20}
          defaultValue={state.values?.username}
          error={state.fieldErrors?.username}
        />
        <TextField
          name="email"
          label="Email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          required
          defaultValue={state.values?.email}
          error={state.fieldErrors?.email}
        />
        <PasswordField
          name="password"
          label="Password"
          placeholder="Create a password"
          autoComplete="new-password"
          required
          minLength={10}
          maxLength={128}
          error={state.fieldErrors?.password}
        />
      </div>
      <p className="auth-form__hint">{PASSWORD_RULES}</p>
      {state.error && (
        <p className="auth-form__alert" role="alert">
          {state.error}
        </p>
      )}
      <WideButton className="auth-form__submit" label={pending ? "Creating…" : "Sign up"} disabled={pending} />
    </form>
  );
}
