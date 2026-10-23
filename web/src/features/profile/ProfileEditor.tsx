"use client";

import { useActionState, useEffect, useId, useRef, useState, type ChangeEvent } from "react";
import { PlayerAvatar } from "@/components/PlayerAvatar/PlayerAvatar";
import { MAX_AVATAR_BYTES } from "@/lib/image-type";
import type { AvatarSource } from "@/lib/profile";
import { removeAvatar, uploadAvatar, type AvatarFormState } from "./actions";

const ACCEPTED_TYPES = "image/png,image/jpeg,image/webp";

interface ProfileEditorProps {
  avatar: AvatarSource;
  name: string;
  hasGooglePhoto: boolean;
  tagline: string;
}

/** Tagline row with the "Edit profile" button, and the profile-picture panel it opens. */
export function ProfileEditor({ avatar, name, hasGooglePhoto, tagline }: ProfileEditorProps) {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<string>();
  const [clientError, setClientError] = useState<string>();
  const [uploadState, uploadAction, uploading] = useActionState<AvatarFormState, FormData>(uploadAvatar, {});
  const [removeState, removeAction, removing] = useActionState<AvatarFormState, FormData>(removeAvatar, {});
  const fileInput = useRef<HTMLInputElement>(null);
  const panelId = useId();

  // Close the panel after a successful save or removal.
  const lastSaved = Math.max(uploadState.savedAt ?? 0, removeState.savedAt ?? 0);
  const handledSave = useRef(0);
  useEffect(() => {
    if (lastSaved > handledSave.current) {
      handledSave.current = lastSaved;
      setOpen(false);
    }
  }, [lastSaved]);

  // Release the object URL used for the local preview.
  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    setClientError(undefined);
    if (!file) return setPreview(undefined);
    // Quick checks for fast feedback; the server re-validates the actual bytes.
    if (file.size > MAX_AVATAR_BYTES) {
      setClientError("That image is too large. Use one under 2 MB.");
      event.target.value = "";
      return setPreview(undefined);
    }
    setPreview(URL.createObjectURL(file));
  }

  function close() {
    setOpen(false);
    setPreview(undefined);
    setClientError(undefined);
    if (fileInput.current) fileInput.current.value = "";
  }

  const error = clientError ?? uploadState.error ?? removeState.error;
  const busy = uploading || removing;
  const fallbackLabel = hasGooglePhoto ? "your Google photo" : "the default explorer";

  return (
    <>
      <div className="player-banner__tagline-row">
        <p className="player-banner__tagline">{tagline}</p>
        <button
          type="button"
          className="profile-edit-button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => (open ? close() : setOpen(true))}
        >
          Edit profile
        </button>
      </div>

      {open && (
        <section className="profile-editor" id={panelId} aria-label="Profile picture">
          <h2 className="profile-editor__title">Profile picture</h2>
          <div className="profile-editor__row">
            <PlayerAvatar avatar={avatar} name={name} previewSrc={preview} />
            <p className="profile-editor__help">
              PNG, JPEG, or WebP, up to 2 MB. Without an uploaded picture, your profile shows {fallbackLabel}.
            </p>
          </div>

          <form action={uploadAction} className="profile-editor__form">
            <label className="profile-editor__file">
              <span className="small-button">Choose picture</span>
              <input
                ref={fileInput}
                className="visually-hidden"
                type="file"
                name="avatar"
                accept={ACCEPTED_TYPES}
                onChange={onFileChange}
                required
              />
            </label>
            <div className="profile-editor__actions">
              <button type="submit" className="small-button small-button--primary" disabled={!preview || busy}>
                {uploading ? "Saving…" : "Save picture"}
              </button>
              <button type="button" className="small-button" onClick={close} disabled={busy}>
                Cancel
              </button>
            </div>
          </form>

          {avatar.kind === "upload" && (
            <form action={removeAction}>
              <button type="submit" className="profile-editor__remove" disabled={busy}>
                {removing ? "Removing…" : `Remove uploaded picture (use ${fallbackLabel})`}
              </button>
            </form>
          )}

          {error && (
            <p className="profile-editor__error" role="alert">
              {error}
            </p>
          )}
        </section>
      )}
    </>
  );
}
