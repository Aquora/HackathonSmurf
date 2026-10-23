import Image, { type StaticImageData } from "next/image";
import Link from "next/link";
import exploreIcon from "@/assets/nav-explore.svg";
import friendsIcon from "@/assets/nav-friends.svg";
import profileIcon from "@/assets/nav-profile.svg";
import questsIcon from "@/assets/nav-quests.svg";
import "./BottomNav.css";

interface NavItem {
  label: string;
  href: string;
  icon: StaticImageData;
  /** Screens that aren't built yet render as disabled tabs. */
  available: boolean;
}

// Icon colors are baked into the Figma SVGs for the Explore-active state.
const ITEMS: NavItem[] = [
  { label: "Explore", href: "/explore", icon: exploreIcon, available: true },
  { label: "Quests", href: "/quests", icon: questsIcon, available: false },
  { label: "Friends", href: "/friends", icon: friendsIcon, available: false },
  { label: "Profile", href: "/profile", icon: profileIcon, available: false },
];

/** App tab bar from the "LocalQuest explore" frame. */
export function BottomNav({ active }: { active: string }) {
  return (
    <nav className="bottom-nav" aria-label="Main">
      <ul className="bottom-nav__tabs">
        {ITEMS.map((item) => {
          const isActive = item.href === active;
          const content = (
            <>
              <Image src={item.icon} alt="" />
              <span>{item.label}</span>
            </>
          );
          const className = `bottom-nav__item bottom-nav__item--${item.label.toLowerCase()}${isActive ? " bottom-nav__item--active" : ""}`;
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
