import { PixelSprite } from "@/components/PixelSprite/PixelSprite";
import { coin } from "@/components/PixelSprite/sprites";
import "./AuthBanner.css";

interface AuthBannerProps {
  title: string;
  highlight: string;
  subtitle: string;
}

/** Red introduction band from the "LocalQuest sign up" frame (Account introduction). */
export function AuthBanner({ title, highlight, subtitle }: AuthBannerProps) {
  return (
    <section className="auth-banner">
      <div className="auth-banner__inner">
        <h1 className="auth-banner__title">
          <span>{title}</span>{" "}
          <span className="auth-banner__highlight">{highlight}</span>
        </h1>
        <p className="auth-banner__subtitle">{subtitle}</p>
        <PixelSprite sprite={coin} className="auth-banner__coin" />
      </div>
      <div className="auth-banner__ground" />
    </section>
  );
}
