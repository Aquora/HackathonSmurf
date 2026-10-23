import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { QuestBoard } from "@/features/quests/QuestBoard";
import { getPlayerProfile } from "@/lib/profile";
import "@/features/quests/quests.css";

export const metadata: Metadata = { title: "Quests · Local Quest" };

/** Signed-in home page: the "LocalQuest quests" Figma frame. */
export default async function QuestsPage() {
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const session = await auth();
  if (!session?.user?.id) redirect("/sign-in?callbackUrl=/quests");

  const profile = await getPlayerProfile(session.user.id);
  if (!profile) redirect("/sign-in?callbackUrl=/quests");
  const firstName = profile.displayName.split(/\s+/)[0];

  return (
    <main className="quests-page">
      <section className="quest-banner" aria-labelledby="quest-board-heading">
        <div className="quest-banner__inner">
          <div className="quest-banner__heading-row">
            <h1 className="quest-banner__heading" id="quest-board-heading">
              Your quest board
            </h1>
            <span className="quest-banner__level">LVL 1</span>
          </div>
          <p className="quest-banner__invite">Little adventures. Right here in your neighborhood.</p>
          <div className="quest-banner__progress">
            <span className="quest-banner__streak">Start a quest to begin your streak, {firstName}!</span>
            <span>0 XP</span>
          </div>
          <div
            className="quest-banner__bar"
            role="progressbar"
            aria-label="Experience"
            aria-valuenow={0}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="quest-banner__fill" style={{ width: "0%" }} />
          </div>
        </div>
        <div className="quest-banner__ground" />
      </section>

      {/* Quests aren't stored yet, so every section shows its empty state. */}
      <QuestBoard />

      <BottomNav active="/quests" />
    </main>
  );
}
