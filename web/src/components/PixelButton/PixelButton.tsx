import type { AnchorHTMLAttributes } from "react";
import playButton from "../../assets/play-button.svg";
import "./PixelButton.css";

interface PixelButtonProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  href: string;
  label: string;
}

/** Red pixel-edged call-to-action from the landing frame, rendered as a link. */
export function PixelButton({ label, className, ...anchorProps }: PixelButtonProps) {
  return (
    <a className={["pixel-button", className].filter(Boolean).join(" ")} {...anchorProps}>
      <img className="pixel-button__frame" src={playButton} alt="" width={140.93} height={75.4986} />
      <span className="pixel-button__label">{label}</span>
    </a>
  );
}
