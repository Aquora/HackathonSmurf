import Link from "next/link";
import { HeaderMenu } from "./HeaderMenu";
import "./AppHeader.css";

/** Top bar shared by every LocalQuest screen: wordmark and menu. */
export function AppHeader() {
  return (
    <header className="app-header">
      <div className="app-header__inner">
        <Link className="app-header__logo" href="/" aria-label="Local Quest home">
          <span className="app-header__logo-local">Local</span>
          <span className="app-header__logo-quest">Quest</span>
        </Link>
        <HeaderMenu />
      </div>
    </header>
  );
}
