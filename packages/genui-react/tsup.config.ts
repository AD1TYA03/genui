import { copyFileSync } from "node:fs";
import { defineConfig } from "tsup";

export default defineConfig({
  entry: { index: "src/index.ts" },
  format: ["esm"],
  dts: true,
  sourcemap: true,
  clean: true,
  target: "es2020",
  treeshake: true,
  // Everything in dependencies/peerDependencies stays external (tsup default).
  async onSuccess() {
    copyFileSync("src/styles.css", "dist/styles.css");
  },
});
