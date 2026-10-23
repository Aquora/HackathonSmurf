import { useLayoutEffect, useRef, useState } from "react";

/**
 * Returns a ref and a scale factor (max 1) that fits `designWidth` into the
 * ref'd element's current width, so fixed-coordinate art shrinks on narrow phones.
 */
export function useFitScale<T extends HTMLElement>(designWidth: number) {
  const ref = useRef<T>(null);
  const [scale, setScale] = useState(1);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const update = () => setScale(Math.min(1, element.clientWidth / designWidth));
    update();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, [designWidth]);

  return [ref, scale] as const;
}
