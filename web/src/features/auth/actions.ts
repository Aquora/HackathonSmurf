"use server";

import { AuthError } from "next-auth";
import { headers } from "next/headers";
import { MongoServerError } from "mongodb";
import { signIn, signOut } from "@/auth";
import { getUsersCollection } from "@/lib/db";
import { hashPassword } from "@/lib/password";
import { clientIp, consume, LIMITS } from "@/lib/rate-limit";
import { registrationSchema, toFieldErrors, type FieldErrors } from "@/lib/validation";
import { safeRedirectPath } from "./redirects";

export interface FormState {
  error?: string;
  fieldErrors?: FieldErrors;
  /** Echoed back so the form keeps non-secret input after an error. */
  values?: { username?: string; email?: string };
}

const GENERIC_SIGN_IN_ERROR = "That username and password don't match. Try again.";
const RATE_LIMITED_ERROR = "Too many attempts. Wait a few minutes and try again.";
const REGISTRATION_CONFLICT =
  "We couldn't create an account with that username or email. Try a different one, or sign in.";

function field(formData: FormData, name: string) {
  const value = formData.get(name);
  return typeof value === "string" ? value : "";
}

export async function signInWithPassword(_previous: FormState, formData: FormData): Promise<FormState> {
  const username = field(formData, "username");
  try {
    await signIn("credentials", {
      username,
      password: field(formData, "password"),
      redirectTo: safeRedirectPath(field(formData, "callbackUrl")),
    });
    return {};
  } catch (error) {
    // A successful sign-in throws Next's redirect; anything that isn't an AuthError must propagate.
    if (!(error instanceof AuthError)) throw error;
    const rateLimited = error.type === "CredentialsSignin" && "code" in error && error.code === "rate_limited";
    return { error: rateLimited ? RATE_LIMITED_ERROR : GENERIC_SIGN_IN_ERROR, values: { username } };
  }
}

export async function signInWithGoogle(formData: FormData) {
  await signIn("google", { redirectTo: safeRedirectPath(field(formData, "callbackUrl")) });
}

export async function registerAccount(_previous: FormState, formData: FormData): Promise<FormState> {
  const values = { username: field(formData, "username"), email: field(formData, "email") };

  if (!consume(`register:${clientIp(await headers())}`, LIMITS.registerPerIp)) {
    return { error: RATE_LIMITED_ERROR, values };
  }

  const parsed = registrationSchema.safeParse({ ...values, password: field(formData, "password") });
  if (!parsed.success) {
    return { fieldErrors: toFieldErrors(parsed.error), values };
  }

  const { username, email, password } = parsed.data;
  const users = await getUsersCollection();
  try {
    // The unique indexes on username and email reject duplicates atomically.
    await users.insertOne({
      name: username,
      username,
      email,
      emailVerified: null,
      passwordHash: await hashPassword(password),
      createdAt: new Date(),
    });
  } catch (error) {
    if (error instanceof MongoServerError && error.code === 11000) {
      return { error: REGISTRATION_CONFLICT, values };
    }
    throw error;
  }

  // Start a session for the new account and continue to the app.
  try {
    await signIn("credentials", { username, password, redirectTo: "/explore" });
  } catch (error) {
    if (!(error instanceof AuthError)) throw error;
    return { error: "Your account was created. Please sign in.", values };
  }
  return {};
}

export async function signOutAction() {
  await signOut({ redirectTo: "/" });
}
