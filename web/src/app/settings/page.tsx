import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { AuthBanner } from "@/components/AuthBanner/AuthBanner";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { SignOutButton } from "@/features/auth/AuthButtons";
import { ProfilePictureForm } from "@/features/profile/ProfilePictureForm";
import { getPlayerProfile } from "@/lib/profile";
import "@/features/profile/profile.css";

export const metadata: Metadata = { title: "Player settings · Local Quest" };

/** Player settings: edit the profile picture and sign out. Opened from the header menu and "Edit profile". */
export default async function SettingsPage() {
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const session = await auth();
  if (!session?.user?.id) redirect("/sign-in?callbackUrl=/settings");

  const profile = await getPlayerProfile(session.user.id);
  if (!profile) redirect("/sign-in?callbackUrl=/settings");

  return (
    <main className="settings-page">
      <AuthBanner title="Player" highlight="settings." subtitle="Edit your profile and manage your account." />

      <div className="settings-page__content">
        <ProfilePictureForm avatar={profile.avatar} name={profile.displayName} hasGooglePhoto={profile.hasGooglePhoto} />

        <section className="profile-editor" aria-labelledby="account-heading">
          <h2 className="profile-editor__title" id="account-heading">
            Account
          </h2>
          <dl className="settings-account">
            {profile.username && (
              <div>
                <dt>Username</dt>
                <dd>@{profile.username}</dd>
              </div>
            )}
            {session.user.email && (
              <div>
                <dt>Email</dt>
                <dd>{session.user.email}</dd>
              </div>
            )}
          </dl>
          <SignOutButton variant="wide" />
        </section>
      </div>

      <BottomNav active="/profile" />
    </main>
  );
}
