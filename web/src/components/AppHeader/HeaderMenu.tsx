"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import chevronRight from "@/assets/chevron-right.svg";
import menuButton from "@/assets/menu-button.svg";

// Items from the Figma "Menu dropdown" (profile frame). Support has no destination yet,
// so it renders as "coming soon".
const ITEMS = [
  { label: "Player settings", href: "/settings" },
  { label: "Support", href: null },
] as const;

/** Header menu button and the dropdown it opens. */
export function HeaderMenu() {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const container = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const items = useRef<(HTMLElement | null)[]>([]);
  const pathname = usePathname();
  const [openedOn, setOpenedOn] = useState(pathname);

  // Close after navigating (state adjusted during render rather than in an effect).
  if (openedOn !== pathname) {
    setOpenedOn(pathname);
    setOpen(false);
  }

  // Close on a click or tap outside the menu.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function focusItem(index: number) {
    const count = ITEMS.length;
    items.current[(index + count) % count]?.focus();
  }

  function openMenu(focusIndex = 0) {
    setOpen(true);
    // Wait for the menu to render before moving focus into it.
    requestAnimationFrame(() => focusItem(focusIndex));
  }

  function close({ restoreFocus }: { restoreFocus: boolean }) {
    setOpen(false);
    if (restoreFocus) button.current?.focus();
  }

  function onButtonKeyDown(event: KeyboardEvent) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      openMenu(event.key === "ArrowDown" ? 0 : ITEMS.length - 1);
    }
  }

  function onMenuKeyDown(event: KeyboardEvent) {
    const current = items.current.indexOf(document.activeElement as HTMLElement);
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        focusItem(current + 1);
        break;
      case "ArrowUp":
        event.preventDefault();
        focusItem(current - 1);
        break;
      case "Home":
        event.preventDefault();
        focusItem(0);
        break;
      case "End":
        event.preventDefault();
        focusItem(ITEMS.length - 1);
        break;
      case "Escape":
        event.preventDefault();
        close({ restoreFocus: true });
        break;
      case "Tab":
        close({ restoreFocus: false });
        break;
    }
  }

  return (
    <div className="header-menu" ref={container}>
      <button
        ref={button}
        type="button"
        className="app-header__menu"
        aria-label="Menu"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => (open ? close({ restoreFocus: false }) : openMenu())}
        onKeyDown={onButtonKeyDown}
      >
        <Image src={menuButton} alt="" priority />
      </button>

      {open && (
        <ul className="header-menu__dropdown" id={menuId} role="menu" aria-label="Menu" onKeyDown={onMenuKeyDown}>
          {ITEMS.map((item, index) => {
            const content = (
              <>
                <span>{item.label}</span>
                <Image src={chevronRight} alt="" />
              </>
            );
            return (
              <li key={item.label} role="none">
                {item.href ? (
                  <Link
                    ref={(element) => {
                      items.current[index] = element;
                    }}
                    className="header-menu__item"
                    href={item.href}
                    role="menuitem"
                    tabIndex={-1}
                    onClick={() => setOpen(false)}
                  >
                    {content}
                  </Link>
                ) : (
                  <span
                    ref={(element) => {
                      items.current[index] = element;
                    }}
                    className="header-menu__item header-menu__item--soon"
                    role="menuitem"
                    aria-disabled="true"
                    tabIndex={-1}
                    title="Coming soon"
                  >
                    {content}
                    <span className="visually-hidden"> (coming soon)</span>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
