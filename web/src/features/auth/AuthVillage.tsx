import { PixelSprite } from "@/components/PixelSprite/PixelSprite";
import { shop } from "@/components/PixelSprite/sprites";

/** Row of pixel shops on a strip of ground, from the bottom of the sign-up frame. */
export function AuthVillage() {
  return (
    <div className="auth-village" aria-hidden="true">
      <div className="auth-village__shops">
        <PixelSprite sprite={shop} />
        <PixelSprite sprite={shop} />
        <PixelSprite sprite={shop} />
      </div>
      <div className="auth-village__ground" />
    </div>
  );
}
