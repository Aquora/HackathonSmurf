"use client";

import type { CSSProperties } from "react";
import { PixelButton } from "../../components/PixelButton/PixelButton";
import { PixelSprite } from "../../components/PixelSprite/PixelSprite";
import { coin, heart, house, shop, star } from "../../components/PixelSprite/sprites";
import { HeroTitle } from "./HeroTitle";
import { useFitScale } from "./useFitScale";
import "./LandingPage.css";

// Hero art is laid out in Figma coordinates (440 wide, measured from below the header).
const HERO_DESIGN_WIDTH = 440;
const HERO_DESIGN_HEIGHT = 388;

const HERO_COINS = [
  { left: 304, top: 70 },
  { left: 344, top: 153 },
  { left: 326, top: 254 },
];

export const SIGN_UP_HREF = "/register";

export function LandingPage() {
  const [heroRef, heroScale] = useFitScale<HTMLDivElement>(HERO_DESIGN_WIDTH);

  return (
    <main className="landing">
      <section className="landing-hero">
        <div className="landing-hero__fit" ref={heroRef} style={{ height: HERO_DESIGN_HEIGHT * heroScale }}>
          <div className="landing-hero__canvas" style={{ "--hero-scale": heroScale } as CSSProperties}>
            <HeroTitle />
            <p className="landing-hero__tagline">
              Bored at home?
              <br />
              Touch some grass.
            </p>
            {HERO_COINS.map((position) => (
              <PixelSprite key={`${position.left},${position.top}`} sprite={coin} className="landing-hero__coin" style={position} />
            ))}
          </div>
        </div>
        <div className="landing-hero__village">
          <PixelSprite sprite={house} />
          <PixelSprite sprite={shop} />
          <PixelSprite sprite={house} />
        </div>
        <div className="landing-hero__grass" />
      </section>

      <section className="landing-intro">
        <p className="landing-intro__text">
          Discover new places, new experiences, and new friends all while playing a game.
        </p>
        <PixelButton className="landing-intro__play" href={SIGN_UP_HREF} label="Play" />
        <div className="landing-intro__decorations">
          <PixelSprite sprite={coin} />
          <PixelSprite sprite={heart} />
          <PixelSprite sprite={star} />
        </div>
      </section>
    </main>
  );
}
