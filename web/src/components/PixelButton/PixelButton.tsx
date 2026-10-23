import type { ComponentProps } from "react";
import Image from "next/image";
import Link from "next/link";
import playButton from "@/assets/play-button.svg";
import "./PixelButton.css";

interface PixelButtonProps extends Omit<ComponentProps<typeof Link>, "children"> {
  label: string;
}

/** Red pixel-edged call-to-action from the landing frame, rendered as a link. */
export function PixelButton({ label, className, ...linkProps }: PixelButtonProps) {
  return (
    <Link className={["pixel-button", className].filter(Boolean).join(" ")} {...linkProps}>
      <Image className="pixel-button__frame" src={playButton} alt="" />
      <span className="pixel-button__label">{label}</span>
    </Link>
  );
}
