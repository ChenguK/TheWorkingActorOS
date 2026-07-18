import path from "node:path";
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import importPlugin from "eslint-plugin-import";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

const rootDirectory = path.dirname(fileURLToPath(import.meta.url));
const sourceDirectory = path.join(rootDirectory, "src");

function sourcePath(filename) {
  return path.relative(sourceDirectory, filename).split(path.sep).join("/");
}

function resolveLocalImport(filename, importSource) {
  let candidate;
  if (importSource === "@") {
    candidate = sourceDirectory;
  } else if (importSource.startsWith("@/")) {
    candidate = path.join(sourceDirectory, importSource.slice(2));
  } else if (importSource.startsWith(".")) {
    candidate = path.resolve(path.dirname(filename), importSource);
  } else {
    return null;
  }

  const relative = sourcePath(candidate).replace(/\.(?:[cm]?[jt]sx?)$/, "");
  return relative.endsWith("/index") ? relative.slice(0, -6) : relative;
}

function featureName(relativePath) {
  const match = relativePath.match(/^features\/([^/]+)(?:\/|$)/);
  return match?.[1] ?? null;
}

const architecturePlugin = {
  rules: {
    imports: {
      meta: {
        type: "problem",
        docs: { description: "Enforce frontend dependency direction and public feature APIs." },
        schema: [],
        messages: {
          removedPath: "Imports from removed compatibility path '{{source}}' are forbidden.",
          pageDependency: "Pages may only import feature public APIs and approved shared modules.",
          pageFeatureInternal: "Pages must import feature '{{feature}}' through its public index.ts API.",
          featureDependency: "Features may only import their own internals, another feature's public API, and approved shared modules.",
          crossFeatureInternal: "Feature '{{importer}}' must import feature '{{target}}' through its public index.ts API.",
          sharedDependency: "Shared UI must not import features or pages.",
          designSystemDependency: "The design system must not import features, pages, services, or React components.",
          directApi: "The shared API client is restricted to service/API and approved infrastructure modules.",
          barrelPage: "Feature barrels must not export page components.",
          barrelFeature: "Feature barrels must not export another feature's implementation."
        }
      },
      create(context) {
        const filename = context.filename;
        const importer = sourcePath(filename);
        const importerFeature = featureName(importer);
        const isFeatureBarrel = /^features\/[^/]+\/index\.[cm]?[jt]sx?$/.test(importer);

        function check(node) {
          const rawSource = node.source?.value;
          if (typeof rawSource !== "string") return;
          const target = resolveLocalImport(filename, rawSource);

          if (/workflowPanels/.test(rawSource) || target === "api/client") {
            context.report({ node: node.source, messageId: "removedPath", data: { source: rawSource } });
            return;
          }
          if (!target) return;

          const targetFeature = featureName(target);
          const importsFeatureRoot = targetFeature && target === `features/${targetFeature}`;
          const targetRoot = target.split("/", 1)[0];
          const approvedSharedRoots = new Set([
            "components",
            "constants",
            "design-system",
            "hooks",
            "services",
            "types",
            "utilities",
            "utils"
          ]);
          if (/\.(?:test|spec)\.[cm]?[jt]sx?$/.test(importer)) approvedSharedRoots.add("test");
          if (importer.startsWith("pages/") && targetFeature && !importsFeatureRoot) {
            context.report({ node: node.source, messageId: "pageFeatureInternal", data: { feature: targetFeature } });
          }
          if (importer.startsWith("pages/") && !targetFeature && !approvedSharedRoots.has(targetRoot)) {
            context.report({ node: node.source, messageId: "pageDependency" });
          }
          if (importerFeature && targetFeature && importerFeature !== targetFeature && !importsFeatureRoot) {
            context.report({
              node: node.source,
              messageId: "crossFeatureInternal",
              data: { importer: importerFeature, target: targetFeature }
            });
          }
          if (importerFeature && !targetFeature && !approvedSharedRoots.has(targetRoot)) {
            context.report({ node: node.source, messageId: "featureDependency" });
          }
          if (importer.startsWith("components/") && /^(?:features|pages)\//.test(target)) {
            context.report({ node: node.source, messageId: "sharedDependency" });
          }
          if (importer.startsWith("design-system/") && /^(?:features|pages|services|components)\//.test(target)) {
            context.report({ node: node.source, messageId: "designSystemDependency" });
          }

          const importsBaseApi = target === "services/api" || target === "services/api/client";
          const apiAllowed = importer.startsWith("services/api/")
            || importer === "services/system/api.ts"
            || /^features\/[^/]+\/api(?:\/|$)/.test(importer)
            || importer.startsWith("app/api/")
            || importer.endsWith(".test.ts")
            || importer.endsWith(".test.tsx");
          if (importsBaseApi && !apiAllowed) {
            context.report({ node: node.source, messageId: "directApi" });
          }

          if (isFeatureBarrel && target.startsWith("pages/")) {
            context.report({ node: node.source, messageId: "barrelPage" });
          }
          if (isFeatureBarrel && targetFeature && targetFeature !== importerFeature) {
            context.report({ node: node.source, messageId: "barrelFeature" });
          }
        }

        return {
          ImportDeclaration: check,
          ExportAllDeclaration: check,
          ExportNamedDeclaration: check
        };
      }
    }
  }
};

export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "coverage/**",
      "node_modules/**",
      "generated/**",
      "**/*.generated.*",
      "**/bundle-report/**",
      "**/bundle-reports/**",
      "**/*.bundle-report.*",
      "tmp/**",
      "temp/**"
    ]
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["eslint.config.js", "scripts/**/*.{js,mjs,cjs}"],
    languageOptions: {
      globals: globals.node
    }
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      globals: { ...globals.browser, ...globals.es2020 }
    },
    plugins: {
      architecture: architecturePlugin,
      import: importPlugin,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh
    },
    settings: {
      "import/resolver": {
        typescript: { project: path.join(rootDirectory, "tsconfig.json") }
      }
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "architecture/imports": "error",
      "import/no-cycle": ["error", { ignoreExternal: true, maxDepth: 20 }],
      "import/no-unresolved": ["error", { commonjs: true, caseSensitive: true }],
      "react-hooks/exhaustive-deps": "error",
      "react-refresh/only-export-components": "off",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": "off"
    }
  },
  {
    files: ["src/App.tsx", "src/pages/**/*.tsx"],
    rules: {
      "react-refresh/only-export-components": ["error", { allowConstantExport: true }]
    }
  },
  {
    files: ["src/**/*.{test,spec}.{ts,tsx}", "src/test/**/*.{ts,tsx}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        afterAll: "readonly",
        afterEach: "readonly",
        beforeAll: "readonly",
        beforeEach: "readonly",
        describe: "readonly",
        expect: "readonly",
        it: "readonly",
        test: "readonly",
        vi: "readonly"
      }
    },
    rules: {
      "react-refresh/only-export-components": "off"
    }
  }
);
