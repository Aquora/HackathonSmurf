import type { CSSProperties } from "react";
import type { PixelColor, Sprite } from "./sprites";

const PIXEL_HEIGHT = 4;

const fill: Record<PixelColor, string> = {
  dark: "var(--pixel-dark)",
  salmon: "var(--pixel-salmon)",
  gold: "var(--pixel-gold)",
  cream: "var(--pixel-cream)",
  light: "var(--pixel-light)",
};

interface PixelSpriteProps {
  sprite: Sprite;
  className?: string;
  style?: CSSProperties;
}

/** Decorative pixel-art sprite. Scales with its CSS width; keeps hard pixel edges. */
export function PixelSprite({ sprite, className, style }: PixelSpriteProps) {
  return (
    <svg
      className={className}
      style={style}
      width={sprite.width}
      height={sprite.height}
      viewBox={`0 0 ${sprite.width} ${sprite.height}`}
      shapeRendering="crispEdges"
      overflow="visible"
      aria-hidden="true"
      focusable="false"
    >
      {sprite.rows.map(([y, ...runs]) =>
        runs.map(([x, width, color]) => (
          <rect key={`${x},${y}`} x={x} y={y} width={width} height={PIXEL_HEIGHT} fill={fill[color]} />
        )),
      )}
    </svg>
  );
}
