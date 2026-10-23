"use client";

import { useActionState, useEffect, useId, useRef, useState } from "react";
import Image from "next/image";
import creamButton from "@/assets/wide-button-cream-48.svg";
import searchIcon from "@/assets/search.svg";
import { sendFriendRequest, type AddFriendState } from "./actions";

/** "+ Add friend" button and the popup it opens (Figma "Add friend popup", 2034:3). */
export function AddFriendPopup() {
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState<AddFriendState, FormData>(sendFriendRequest, {});
  const popupId = useId();
  const inputId = useId();
  const toggle = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);

  function openPopup() {
    setOpen(true);
    requestAnimationFrame(() => input.current?.focus());
  }

  // Escape closes the popup wherever focus is, and returns focus to the button.
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setOpen(false);
      toggle.current?.focus();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      <button
        ref={toggle}
        type="button"
        className="add-friend-toggle"
        aria-expanded={open}
        aria-controls={popupId}
        onClick={() => (open ? setOpen(false) : openPopup())}
      >
        <Image className="add-friend-toggle__frame" src={creamButton} alt="" />
        <span className="add-friend-toggle__label">+ Add friend</span>
      </button>

      {open && (
        <section className="add-friend-popup" id={popupId} aria-labelledby={`${popupId}-title`}>
          <h2 className="add-friend-popup__title" id={`${popupId}-title`}>
            Add friend
          </h2>

          <form action={formAction} className="add-friend-popup__form">
            <label className="add-friend-popup__field" htmlFor={inputId}>
              <Image src={searchIcon} alt="" />
              <span className="visually-hidden">Friend&apos;s name or username</span>
              <input
                ref={input}
                id={inputId}
                className="add-friend-popup__input"
                name="query"
                placeholder="Name or username"
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                maxLength={60}
                required
              />
            </label>
            <button type="submit" className="add-friend-popup__submit" disabled={pending}>
              {pending ? "Sending…" : "Add friend"}
            </button>
          </form>

          {state.error && (
            <p className="add-friend-popup__error" role="alert">
              {state.error}
            </p>
          )}
          {state.message && (
            <p className="add-friend-popup__message" role="status">
              {state.message}
            </p>
          )}
          {state.choices && (
            <ul className="add-friend-popup__choices">
              {state.choices.map((player) => (
                <li key={player.id}>
                  <form action={formAction}>
                    <input type="hidden" name="targetId" value={player.id} />
                    <button type="submit" className="add-friend-popup__choice" disabled={pending}>
                      <span>{player.name}</span>
                      {player.username && <span className="add-friend-popup__handle">@{player.username}</span>}
                    </button>
                  </form>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  );
}
