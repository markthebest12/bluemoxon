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
  // Allow any for now (can tighten later)
  "@typescript-eslint/no-explicit-any": "off",
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

  // Vue 3 essential rules
  ...vue.configs["flat/essential"],

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

  // Prettier must be last - disables conflicting rules
  prettier,
];
