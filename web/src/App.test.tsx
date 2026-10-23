import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";

afterEach(() => {
  window.location.hash = "";
});

describe("landing page", () => {
  it("shows the hero heading, tagline, and intro copy", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "Local Quest" })).toBeInTheDocument();
    expect(screen.getByText(/Bored at home\?/)).toBeInTheDocument();
    expect(screen.getByText(/Discover new places/)).toBeInTheDocument();
  });

  it("has a keyboard-reachable menu button and home link in the header", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: "Open menu" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Local Quest home" })).toHaveAttribute("href", "#/");
  });

  it("Play navigates to the sign-up route", async () => {
    render(<App />);
    const play = screen.getByRole("link", { name: "Play" });
    expect(play).toHaveAttribute("href", "#/sign-up");

    await act(async () => {
      window.location.hash = "#/sign-up";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(screen.getByText("Sign up is not built yet.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Play" })).not.toBeInTheDocument();
  });
});
