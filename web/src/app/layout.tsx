import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "@fontsource/jersey-10";
import "@fontsource/jersey-15";
import "@fontsource/jersey-20";
import "@/styles/global.css";
import { AppHeader } from "@/components/AppHeader/AppHeader";

export const metadata: Metadata = {
  title: "Local Quest",
  description: "Discover new places, new experiences, and new friends all while playing a game.",
};

export const viewport: Viewport = {
  themeColor: "#b13e3e",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppHeader />
        {children}
      </body>
    </html>
  );
}
