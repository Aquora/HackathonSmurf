import { describe, expect, it } from "vitest";
import { sniffImageType } from "./image-type";

const bytes = (...values: number[]) => new Uint8Array(values);
const ascii = (text: string) => new TextEncoder().encode(text);

describe("sniffImageType", () => {
  it("recognizes PNG, JPEG, and WebP by their signatures", () => {
    expect(sniffImageType(bytes(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0))).toBe("image/png");
    expect(sniffImageType(bytes(0xff, 0xd8, 0xff, 0xe0))).toBe("image/jpeg");
    expect(sniffImageType(new Uint8Array([...ascii("RIFF"), 0, 0, 0, 0, ...ascii("WEBPVP8 ")]))).toBe("image/webp");
  });

  it("rejects SVG, GIF, HTML, and truncated or empty input", () => {
    expect(sniffImageType(ascii('<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>'))).toBeNull();
    expect(sniffImageType(ascii("GIF89a"))).toBeNull();
    expect(sniffImageType(ascii("<html><script>alert(1)</script>"))).toBeNull();
    expect(sniffImageType(new Uint8Array([...ascii("RIFF"), 0, 0, 0, 0, ...ascii("WAVE")]))).toBeNull();
    expect(sniffImageType(bytes(0x89, 0x50))).toBeNull();
    expect(sniffImageType(new Uint8Array())).toBeNull();
  });
});
