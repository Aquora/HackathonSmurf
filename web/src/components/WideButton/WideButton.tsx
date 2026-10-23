import type { ButtonHTMLAttributes } from "react";
import Image from "next/image";
import wideButton from "@/assets/wide-button.svg";
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
