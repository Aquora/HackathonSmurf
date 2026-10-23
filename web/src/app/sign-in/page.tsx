import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { auth } from "@/auth";
import { AuthBanner } from "@/components/AuthBanner/AuthBanner";
import { GoogleSignIn, SignOutButton } from "@/features/auth/AuthButtons";
import { safeRedirectPath, signInErrorMessage } from "@/features/auth/redirects";
import { SignInForm } from "@/features/auth/SignInForm";
import { AuthVillage } from "@/features/auth/AuthVillage";
import "@/features/auth/auth-pages.css";

export const metadata: Metadata = { title: "Sign in · Local Quest" };

interface SignInPageProps {
  searchParams: Promise<{ error?: string; callbackUrl?: string }>;
}

export default async function SignInPage({ searchParams }: SignInPageProps) {
  const [{ error, callbackUrl }, session, requestHeaders] = await Promise.all([searchParams, auth(), headers()]);
  const destination = safeRedirectPath(callbackUrl, requestHeaders.get("host"));

  if (session?.user) {
    const who = session.user.username ? `@${session.user.username}` : (session.user.email ?? "your account");
    return (
      <main>
        <AuthBanner title="Welcome" highlight="back, player." subtitle={`You're signed in as ${who}.`} />
        <div className="auth-page">
          <Link className="auth-page__continue" href={destination}>
            Continue to your quests
          </Link>
          <SignOutButton variant="wide" />
        </div>
      </main>
    );
  }

  return (
    <main>
      <AuthBanner title="Welcome" highlight="back, player." subtitle="Sign in to continue your quest." />
      <div className="auth-page">
        <SignInForm callbackUrl={destination} initialError={signInErrorMessage(error)} />
        <GoogleSignIn callbackUrl={destination} />
        <p className="auth-page__switch">
          <span>New player?</span>
          <Link href="/register">Create an account</Link>
        </p>
      </div>
      <AuthVillage />
    </main>
  );
}
