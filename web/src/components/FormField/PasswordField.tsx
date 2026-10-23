"use client";

import { useState, type ComponentProps } from "react";
import Image from "next/image";
import showPassword from "@/assets/show-password.svg";
import { TextField } from "./TextField";

type PasswordFieldProps = Omit<ComponentProps<typeof TextField>, "type" | "adornment">;

/** Password input with the eye toggle from the sign-up frame. */
export function PasswordField(props: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  return (
    <TextField
      {...props}
      type={visible ? "text" : "password"}
      adornment={
        <button
          type="button"
          className="form-field__toggle"
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          onClick={() => setVisible((current) => !current)}
        >
          <Image src={showPassword} alt="" />
        </button>
      }
    />
  );
}
