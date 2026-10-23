import { ObjectId } from "mongodb";
import { describe, expect, it } from "vitest";
import { initials, pairKey } from "./friends";

describe("friends helpers", () => {
  it("builds the same pair key regardless of who sent the request", () => {
    const a = new ObjectId();
    const b = new ObjectId();
    expect(pairKey(a, b)).toBe(pairKey(b, a));
    expect(pairKey(a, b)).not.toBe(pairKey(a, new ObjectId()));
  });

  it.each([
    ["Alex Morgan", "AM"],
    ["Noah   Williams", "NW"],
    ["Mary Jane Watson", "MW"],
    ["samonthetrail", "SA"],
  ])("initials(%s) = %s", (name, expected) => {
    expect(initials(name)).toBe(expected);
  });
});
