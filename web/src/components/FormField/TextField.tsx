import type { InputHTMLAttributes, ReactNode } from "react";
import "./FormField.css";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  name: string;
  label: string;
  error?: string;
  /** Extra control rendered inside the input box (e.g. a show-password toggle). */
  adornment?: ReactNode;
}

/** Labelled pixel-style input from the sign-up frame, with an accessible inline error. */
export function TextField({ name, label, error, adornment, id = name, ...inputProps }: TextFieldProps) {
  const errorId = `${id}-error`;
  return (
    <div className="form-field">
      <label className="form-field__label" htmlFor={id}>
        {label}
      </label>
      <div className={`form-field__box${error ? " form-field__box--invalid" : ""}`}>
        <input
          className="form-field__input"
          id={id}
          name={name}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          {...inputProps}
        />
        {adornment}
      </div>
      {error && (
        <p className="form-field__error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  );
}
