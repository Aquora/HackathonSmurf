import Image, { type StaticImageData } from "next/image";
import backpack from "@/assets/avatar/backpack.svg";
import backpackStraps from "@/assets/avatar/backpack-straps.svg";
import cap from "@/assets/avatar/cap.svg";
import face from "@/assets/avatar/face.svg";
import hair from "@/assets/avatar/hair.svg";
import head from "@/assets/avatar/head.svg";
import neck from "@/assets/avatar/neck.svg";
import shirt from "@/assets/avatar/shirt.svg";
import type { AvatarSource } from "@/lib/profile";
import "./PlayerAvatar.css";

// Layers of the Figma "Explorer avatar", bottom to top, with their insets in the 80px frame.
const EXPLORER_LAYERS: { src: StaticImageData; inset: string }[] = [
  { src: backpack, inset: "62.5% 16.25% 8.75% 16.25%" },
  { src: shirt, inset: "63.75% 16.25% 7.5% 16.25%" },
  { src: neck, inset: "58.75% 37.5% 23.75% 37.5%" },
  { src: backpackStraps, inset: "70% 28.75% 12.5% 28.75%" },
  { src: head, inset: "27.5% 21.25% 31.25% 21.25%" },
  { src: hair, inset: "31.25% 26.25% 52.5% 26.25%" },
  { src: face, inset: "45% 33.75% 37.5% 33.75%" },
  { src: cap, inset: "8.75% 21.25% 62.5% 23.75%" },
];

function DefaultExplorer() {
  return (
    <span className="player-avatar__explorer">
      {EXPLORER_LAYERS.map(({ src, inset }) => (
        <Image key={src.src} src={src} alt="" className="player-avatar__layer" style={{ inset }} />
      ))}
    </span>
  );
}

interface PlayerAvatarProps {
  avatar: AvatarSource;
  name: string;
  /** Local preview of a picture the user picked but hasn't saved yet. */
  previewSrc?: string;
}

/** 88px framed profile picture: uploaded picture, Google photo, or the default pixel explorer. */
export function PlayerAvatar({ avatar, name, previewSrc }: PlayerAvatarProps) {
  const label = `${name}'s profile picture`;
  return (
    <span className="player-avatar" role="img" aria-label={label}>
      {previewSrc ? (
        // Object URL of a local file; next/image can't optimize it.
        // eslint-disable-next-line @next/next/no-img-element
        <img className="player-avatar__photo" src={previewSrc} alt="" />
      ) : avatar.kind === "default" ? (
        <DefaultExplorer />
      ) : (
        <Image
          className="player-avatar__photo"
          src={avatar.src}
          alt=""
          width={80}
          height={80}
          // Uploaded pictures need the viewer's session cookie, which the image optimizer doesn't send.
          unoptimized={avatar.kind === "upload"}
          referrerPolicy="no-referrer"
        />
      )}
    </span>
  );
}
