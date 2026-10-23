import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { AuthBanner } from "@/components/AuthBanner/AuthBanner";
import { GoogleSignIn } from "@/features/auth/AuthButtons";
import { AuthVillage } from "@/features/auth/AuthVillage";
import { DEFAULT_AFTER_SIGN_IN } from "@/features/auth/redirects";
import { RegisterForm } from "@/features/auth/RegisterForm";
import "@/features/auth/auth-pages.css";

export const metadata: Metadata = { title: "Create an account · Local Quest" };

export default async function RegisterPage() {
  if ((await auth())?.user) redirect(DEFAULT_AFTER_SIGN_IN);

  return (
    <main>
      <AuthBanner title="Your quest" highlight="starts here." subtitle="Create an account. Let’s explore together." />
      <div className="auth-page">
        <RegisterForm />
        <GoogleSignIn callbackUrl={DEFAULT_AFTER_SIGN_IN} />
        <p className="auth-page__switch">
          <span>Already a player?</span>
          <Link href="/sign-in">Sign in</Link>
        </p>
      </div>
      <AuthVillage />
    </main>
  );
}
