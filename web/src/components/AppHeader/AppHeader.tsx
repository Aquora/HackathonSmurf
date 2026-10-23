import menuButton from "../../assets/menu-button.svg";
import "./AppHeader.css";

interface AppHeaderProps {
  onMenuClick?: () => void;
}

/** Top bar shared by every LocalQuest screen: wordmark and menu button. */
export function AppHeader({ onMenuClick }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header__inner">
        <a className="app-header__logo" href="#/" aria-label="Local Quest home">
          <span className="app-header__logo-local">Local</span>
          <span className="app-header__logo-quest">Quest</span>
        </a>
        <button type="button" className="app-header__menu" aria-label="Open menu" onClick={onMenuClick}>
          <img src={menuButton} alt="" width={68} height={39} />
        </button>
      </div>
    </header>
  );
}
