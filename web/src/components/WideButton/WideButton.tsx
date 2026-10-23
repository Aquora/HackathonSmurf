import type { ButtonHTMLAttributes } from "react";
import Image from "next/image";
import Link from "next/link";
import wideButton from "@/assets/wide-button.svg";
import wideButton56 from "@/assets/wide-button-56.svg";
import "./WideButton.css";

interface WideButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  /** "primary" is the 44px "Sign up" label; "secondary" is the 34px "Google" label. */
  size?: "primary" | "secondary";
}

/** Full-width 376x64 pixel button from the sign-up frame. */
export function WideButton({ label, size = "primary", className, type = "submit", ...buttonProps }: WideButtonProps) {
  return (
    <button
      type={type}
      className={["wide-button", `wide-button--${size}`, className].filter(Boolean).join(" ")}
      {...buttonProps}
    >
      <Image className="wide-button__frame" src={wideButton} alt="" />
      <span className="wide-button__label">{label}</span>
    </button>
  );
}

/** Full-width 376x56 pixel link button from the profile frame ("Find your next quest"). */
export function WideLink({ label, href, className }: { label: string; href: string; className?: string }) {
  return (
    <Link className={["wide-button", "wide-button--compact", className].filter(Boolean).join(" ")} href={href}>
      <Image className="wide-button__frame" src={wideButton56} alt="" />
      <span className="wide-button__label">{label}</span>
    </Link>
  );
}
