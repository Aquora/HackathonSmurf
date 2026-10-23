"use client";

import { useActionState, useEffect, useState, type ChangeEvent } from "react";
import { PlayerAvatar } from "@/components/PlayerAvatar/PlayerAvatar";
import { MAX_AVATAR_BYTES } from "@/lib/image-type";
import type { AvatarSource } from "@/lib/profile";
import { removeAvatar, uploadAvatar, type AvatarFormState } from "./actions";

const ACCEPTED_TYPES = "image/png,image/jpeg,image/webp";

interface ProfilePictureFormProps {
  avatar: AvatarSource;
  name: string;
  hasGooglePhoto: boolean;
}

/** Profile-picture panel on the Player settings page: preview, upload, and remove. */
export function ProfilePictureForm({ avatar, name, hasGooglePhoto }: ProfilePictureFormProps) {
  const [preview, setPreview] = useState<string>();
  const [clientError, setClientError] = useState<string>();
  const [uploadState, uploadAction, uploading] = useActionState<AvatarFormState, FormData>(uploadAvatar, {});
  const [removeState, removeAction, removing] = useActionState<AvatarFormState, FormData>(removeAvatar, {});

  // After a successful save or removal, drop the local preview (adjusted during render).
  // React resets the file input itself once the form action succeeds.
  const lastSaved = Math.max(uploadState.savedAt ?? 0, removeState.savedAt ?? 0);
  const [handledSave, setHandledSave] = useState(0);
  if (lastSaved > handledSave) {
    setHandledSave(lastSaved);
    setPreview(undefined);
  }

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

  const error = clientError ?? uploadState.error ?? removeState.error;
  const busy = uploading || removing;
  const fallbackLabel = hasGooglePhoto ? "your Google photo" : "the default explorer";
  const saved = !error && !preview && lastSaved > 0;

  return (
    <section className="profile-editor" aria-labelledby="profile-picture-heading">
      <h2 className="profile-editor__title" id="profile-picture-heading">
        Profile picture
      </h2>
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
            className="visually-hidden"
            type="file"
            name="avatar"
            accept={ACCEPTED_TYPES}
            onChange={onFileChange}
            required
          />
        </label>
        {preview && (
          <div className="profile-editor__actions">
            <button type="submit" className="small-button small-button--primary" disabled={busy}>
              {uploading ? "Saving…" : "Save picture"}
            </button>
            <button type="reset" className="small-button" onClick={() => setPreview(undefined)} disabled={busy}>
              Cancel
            </button>
          </div>
        )}
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
      {saved && (
        <p className="profile-editor__status" role="status">
          Profile picture updated.
        </p>
      )}
    </section>
  );
}
