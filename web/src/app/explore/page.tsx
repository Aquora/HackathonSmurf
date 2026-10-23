import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { SignOutButton } from "@/features/auth/AuthButtons";
import "@/features/auth/auth-pages.css";

export const metadata: Metadata = { title: "Explore · Local Quest" };

export default async function ExplorePage() {
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const session = await auth();
  if (!session?.user) redirect("/sign-in?callbackUrl=/explore");

  const who = session.user.username ? `@${session.user.username}` : (session.user.name ?? session.user.email);

  return (
    <main className="explore-page">
      {/* The Figma Explore frame has no body content yet; only the account bar is added. */}
      <div className="account-bar">
        <p className="account-bar__who">
          Signed in as <strong>{who}</strong>
        </p>
        <SignOutButton />
      </div>
      <BottomNav active="/explore" />
    </main>
  );
}
