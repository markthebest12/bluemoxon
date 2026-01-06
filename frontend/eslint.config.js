import js from "@eslint/js";
import typescript from "typescript-eslint";
import vue from "eslint-plugin-vue";
import vueParser from "vue-eslint-parser";
import prettier from "eslint-config-prettier";
import globals from "globals";

// Shared TypeScript rules for all file types
const sharedTypeScriptRules = {
  // Allow unused vars prefixed with _
  "@typescript-eslint/no-unused-vars": [
    "warn",
    {
      argsIgnorePattern: "^_",
      varsIgnorePattern: "^_",
      caughtErrorsIgnorePattern: "^_",
    },
  ],
  // Disallow explicit any - use proper types instead
  "@typescript-eslint/no-explicit-any": "error",
};

// Type-aware rules that catch real async bugs (#625)
const typeAwareRules = {
  // Catch forgotten awaits - causes silent failures
  "@typescript-eslint/no-floating-promises": "error",
  // Catch accidental promise-in-condition bugs
  "@typescript-eslint/no-misused-promises": "error",
};

export default [
  // Global ignores
  {
    ignores: ["dist/**", "node_modules/**"],
  },

  // Base JS recommended rules
  js.configs.recommended,

  // TypeScript recommended rules (for .ts files)
  ...typescript.configs.recommended,

  // Vue 3 recommended rules (stricter than essential)
  ...vue.configs["flat/recommended"],

  // Vue files with TypeScript support
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: typescript.parser,
        ecmaVersion: "latest",
        sourceType: "module",
      },
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      ...sharedTypeScriptRules,
      "vue/multi-word-component-names": "off",
    },
  },

  // JS/TS files
  {
    files: ["**/*.{js,ts}"],
    languageOptions: {
      ecmaVersion: "latest",
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      ...sharedTypeScriptRules,
    },
  },

  // Type-aware linting for src/ TypeScript files (#625)
  // These rules require type information from tsconfig
  // Excludes test files (__tests__) which aren't in tsconfig.app.json
  {
    files: ["src/**/*.ts"],
    ignores: ["src/**/__tests__/**"],
    languageOptions: {
      parserOptions: {
        project: "./tsconfig.app.json",
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      ...typeAwareRules,
    },
  },

  // Type-aware linting for Vue files (#625)
  // SEPARATE CONFIG REQUIRED: Vue files need extraFileExtensions: [".vue"] in
  // parserOptions to enable type-aware linting. This option is incompatible with
  // .ts files (causes "You cannot use extraFileExtensions for .ts" error), so
  // TypeScript and Vue type-aware configs must be separate blocks.
  {
    files: ["src/**/*.vue"],
    languageOptions: {
      parserOptions: {
        project: "./tsconfig.app.json",
        tsconfigRootDir: import.meta.dirname,
        extraFileExtensions: [".vue"],
      },
    },
    rules: {
      ...typeAwareRules,
    },
  },

  // Prettier must be last - disables conflicting rules
  prettier,
];
