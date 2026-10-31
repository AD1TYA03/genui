import { copyFileSync, readFileSync, writeFileSync } from "node:fs";
import { defineConfig } from "tsup";

export default defineConfig({
  entry: { index: "src/index.ts", core: "src/core.ts" },
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
    for (const entry of ["dist/index.js", "dist/core.js"]) {
      const code = readFileSync(entry, "utf8");
      if (!code.startsWith('import "./devtools.js"')) writeFileSync(entry, 'import "./devtools.js";\n' + code);
    }
  },
});
