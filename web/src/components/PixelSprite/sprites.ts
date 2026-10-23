// Pixel art from the Figma "Main Page" frame, stored as 4px-tall rows of
// horizontal runs instead of one element per pixel.
// Each row is [y, ...runs]; each run is [x, width, color].

export type PixelColor = "dark" | "salmon" | "gold" | "cream" | "light";
type Run = readonly [x: number, width: number, color: PixelColor];
type Row = readonly [y: number, ...runs: Run[]];

export interface Sprite {
  width: number;
  height: number;
  rows: readonly Row[];
}

const D = "dark";
const R = "salmon";
const Y = "gold";
const C = "cream";
const L = "light";

const houseWall = (y: number): Row => [y, [8, 4, D], [12, 64, Y], [76, 4, D]];
const houseWindowEdge = (y: number): Row => [
  y, [8, 4, D], [12, 8, Y], [20, 12, C], [32, 20, Y], [52, 12, C], [64, 12, Y], [76, 4, D],
];
const houseDoor = (y: number): Row => [
  y, [8, 4, D], [12, 24, Y], [36, 4, D], [40, 8, L], [48, 4, D], [52, 24, Y], [76, 4, D],
];

export const house: Sprite = {
  width: 88,
  height: 68,
  rows: [
    [0, [36, 16, D]],
    [4, [28, 8, D], [36, 16, R], [52, 8, D]],
    [8, [20, 8, D], [28, 32, R], [60, 8, D]],
    [12, [12, 8, D], [20, 48, R], [68, 8, D]],
    [16, [4, 8, D], [12, 64, R], [76, 8, D]],
    [20, [0, 88, D]],
    houseWall(24),
    houseWall(28),
    houseWindowEdge(32),
    [36, [8, 4, D], [12, 8, Y], [20, 4, C], [24, 4, L], [28, 4, C], [32, 20, Y], [52, 4, C], [56, 4, L], [60, 4, C], [64, 12, Y], [76, 4, D]],
    houseWindowEdge(40),
    [44, [8, 4, D], [12, 24, Y], [36, 16, D], [52, 24, Y], [76, 4, D]],
    houseDoor(48),
    houseDoor(52),
    [56, [8, 4, D], [12, 24, Y], [36, 4, D], [40, 4, L], [44, 8, D], [52, 24, Y], [76, 4, D]],
    houseDoor(60),
    [64, [8, 72, D]],
  ],
};

const checkerRow = (y: number, first: PixelColor, second: PixelColor): Row => [
  y,
  ...Array.from({ length: 10 }, (_, i): Run => [4 + i * 8, 8, i % 2 === 0 ? first : second]),
];
const shopWindows = (y: number, side: PixelColor, middle: PixelColor): Row => [
  y, [4, 4, D], [8, 24, side], [32, 4, D], [36, 16, middle], [52, 4, D], [56, 24, side], [80, 4, D],
];

export const shop: Sprite = {
  width: 88,
  height: 68,
  rows: [
    [0, [8, 72, D]],
    [4, [4, 80, R]],
    [8, [4, 80, C]],
    [12, [4, 80, R]],
    [16, [4, 80, C]],
    [20, [0, 88, D]],
    checkerRow(24, R, C),
    checkerRow(28, C, R),
    [32, ...Array.from({ length: 10 }, (_, i): Run => [4 + i * 8, 4, D])],
    [36, [4, 80, Y]],
    [40, [4, 80, Y]],
    [44, [4, 80, D]],
    shopWindows(48, C, L),
    shopWindows(52, L, Y),
    shopWindows(56, C, D),
    [60, [4, 80, D]],
    [64, [4, 80, D]],
  ],
};

const coinRim = (y: number): Row => [y, [4, 4, D], [8, 16, Y], [24, 4, D]];
const coinWide = (y: number): Row => [y, [0, 4, D], [4, 8, Y], [12, 8, L], [20, 8, Y], [28, 4, D]];
const coinMiddle = (y: number): Row => [y, [0, 4, D], [4, 12, Y], [16, 4, L], [20, 8, Y], [28, 4, D]];

export const coin: Sprite = {
  width: 32,
  height: 32,
  rows: [
    [0, [8, 16, D]],
    coinRim(4),
    coinWide(8),
    coinMiddle(12),
    coinMiddle(16),
    coinWide(20),
    coinRim(24),
    [28, [8, 16, D]],
  ],
};

export const heart: Sprite = {
  width: 32,
  height: 32,
  rows: [
    [0, [4, 8, D], [20, 8, D]],
    [4, [0, 4, D], [4, 8, R], [12, 8, D], [20, 8, R], [28, 4, D]],
    [8, [0, 4, D], [4, 24, R], [28, 4, D]],
    [12, [0, 4, D], [4, 24, R], [28, 4, D]],
    [16, [4, 4, D], [8, 16, R], [24, 4, D]],
    [20, [8, 4, D], [12, 8, R], [20, 4, D]],
    [24, [12, 8, D]],
  ],
};

export const star: Sprite = {
  width: 32,
  height: 32,
  rows: [
    [0, [12, 8, D]],
    [4, [12, 8, D]],
    [8, [0, 12, D], [12, 12, Y], [24, 12, D]],
    [12, [0, 4, D], [4, 24, Y], [28, 4, D]],
    [16, [4, 4, D], [8, 16, Y], [24, 4, D]],
    [20, [8, 4, D], [12, 12, Y], [24, 4, D]],
    [24, [4, 4, D], [8, 16, Y], [24, 4, D]],
    [28, [4, 8, D], [20, 8, D]],
  ],
};
