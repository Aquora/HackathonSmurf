import Image, { type StaticImageData } from "next/image";
import Link from "next/link";
import exploreInactive from "@/assets/nav-explore-inactive.svg";
import friendsInactive from "@/assets/nav-friends-inactive.svg";
import profileActive from "@/assets/nav-profile-active.svg";
import profileInactive from "@/assets/nav-profile-inactive.svg";
import questsActive from "@/assets/nav-quests-active.svg";
import questsInactive from "@/assets/nav-quests-inactive.svg";
import "./BottomNav.css";

interface NavItem {
  label: string;
  href: string;
  /** Icon colors are baked into the Figma SVGs: gold when active, white otherwise. */
  icons: { active?: StaticImageData; inactive: StaticImageData };
  /** Screens that aren't built yet render as disabled tabs. */
  available: boolean;
}

const ITEMS: NavItem[] = [
  // Explore is reserved for a future map view.
  { label: "Explore", href: "/explore", icons: { inactive: exploreInactive }, available: false },
  { label: "Quests", href: "/quests", icons: { active: questsActive, inactive: questsInactive }, available: true },
  { label: "Friends", href: "/friends", icons: { inactive: friendsInactive }, available: false },
  { label: "Profile", href: "/profile", icons: { active: profileActive, inactive: profileInactive }, available: true },
];

/** App tab bar from the "LocalQuest quests" and "player profile" frames. */
export function BottomNav({ active }: { active: string }) {
  return (
    <nav className="bottom-nav" aria-label="Main">
      <div className="bottom-nav__trim" />
      <ul className="bottom-nav__tabs">
        {ITEMS.map((item) => {
          const isActive = item.href === active;
          const content = (
            <>
              <Image src={(isActive && item.icons.active) || item.icons.inactive} alt="" />
              <span>{item.label}</span>
            </>
          );
          const className = `bottom-nav__item${isActive ? " bottom-nav__item--active" : ""}`;
          return (
            <li key={item.href}>
              {item.available ? (
                <Link className={className} href={item.href} aria-current={isActive ? "page" : undefined}>
                  {content}
                </Link>
              ) : (
                <span className={`${className} bottom-nav__item--soon`} aria-disabled="true" title="Coming soon">
                  {content}
                  <span className="visually-hidden"> (coming soon)</span>
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
