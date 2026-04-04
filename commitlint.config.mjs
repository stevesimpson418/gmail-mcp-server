// commitlint.config.mjs — Conventional Commits enforcement
// Uses @commitlint/config-conventional (installed globally via npm)
// Valid format: type(scope): subject
// Examples:  feat: add auth  |  fix(api): resolve null pointer  |  docs: update README

export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // Override: max header length 100 (default is 72)
    "header-max-length": [2, "always", 100],
  },
};
