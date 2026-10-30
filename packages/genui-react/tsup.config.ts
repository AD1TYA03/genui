import { copyFileSync, readFileSync, writeFileSync } from "node:fs";
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
    // OpenUI's renderer checks its devtools flag when it is first evaluated. ES modules
    // evaluate imports in order, so the flag lives in its own file imported first.
    writeFileSync(
      "dist/devtools.js",
      'const g = globalThis;\nif (!g.GENUI_OPENUI_DEVTOOLS) g[Symbol.for("openui.devtools.autoMount")] = true;\n',
    );
    const index = readFileSync("dist/index.js", "utf8");
    if (!index.startsWith('import "./devtools.js"')) writeFileSync("dist/index.js", 'import "./devtools.js";\n' + index);
  },
});
