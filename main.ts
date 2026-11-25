import { copyFileSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";

const outDir = process.argv[2] ?? "output";
mkdirSync(outDir, { recursive: true });
const src = "entry.png";
const size = statSync(src).size;
if (size < 1 || size > 1024 * 1024) {
  throw new Error(`entry.png is ${size} bytes, outside the 1 byte-1 MiB band`);
}
const bytes = readFileSync(src);
if (bytes.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") {
  throw new Error("entry.png is not a PNG file");
}
const width = bytes.readUInt32BE(16);
const height = bytes.readUInt32BE(20);
if (width !== 1024 || height !== 1024) {
  throw new Error(`entry.png is ${width}x${height}, expected 1024x1024`);
}
const sha256 = createHash("sha256").update(bytes).digest("hex");
copyFileSync(src, join(outDir, "entry.png"));
console.log(`copied entry.png (${size} bytes, sha256=${sha256}) -> ${join(outDir, "entry.png")}`);
