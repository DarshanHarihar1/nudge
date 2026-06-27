/** @type {import("eslint").Linter.Config} */
module.exports = {
  extends: ["eslint:recommended"],
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint"],
  rules: {
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/consistent-type-imports": "error",
    "no-console": ["warn", { allow: ["warn", "error"] }],
  },
  ignorePatterns: ["node_modules/", "dist/", ".next/"],
};
