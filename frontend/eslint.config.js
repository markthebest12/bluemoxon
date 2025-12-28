import js from "@eslint/js";
import typescript from "typescript-eslint";
import vue from "eslint-plugin-vue";
import prettier from "eslint-config-prettier";
import globals from "globals";

export default [
  // Base JS recommended rules
  js.configs.recommended,

  // TypeScript recommended rules
  ...typescript.configs.recommended,

  // Vue 3 essential rules
  ...vue.configs["flat/essential"],

  // Project-specific configuration
  {
    files: ["**/*.{js,ts,vue}"],
    languageOptions: {
      ecmaVersion: "latest",
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // Allow unused vars prefixed with _
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // Allow any for now (can tighten later)
      "@typescript-eslint/no-explicit-any": "off",
      // Vue component naming
      "vue/multi-word-component-names": "off",
    },
  },

  // Prettier must be last - disables conflicting rules
  prettier,
];
